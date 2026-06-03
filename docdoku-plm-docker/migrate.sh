#!/usr/bin/env bash
# migrate.sh — DocdokuPLM 数据迁移工具
#
# 用法：
#   ./migrate.sh export            # 导出数据库 + 文件库到当前目录
#   ./migrate.sh import            # 从当前目录导入数据库 + 文件库
#   ./migrate.sh from-volumes      # 一次性：将旧 named volume 数据迁入 ./data/（首次切换时使用）
#
# 说明：
#   - export/import 配合使用，用于跨机器迁移
#   - from-volumes 仅在从旧版 docker-compose（named volume）升级时运行一次

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
BACKUP_DB="$SCRIPT_DIR/backup_db.sql"
BACKUP_VAULT="$SCRIPT_DIR/backup_vault.tar.gz"

# 颜色输出
info()    { echo "[INFO]  $*"; }
success() { echo "[OK]    $*"; }
warn()    { echo "[WARN]  $*"; }
error()   { echo "[ERROR] $*" >&2; exit 1; }

# ─────────────────────────────────────────────
# export：导出数据库和文件库
# ─────────────────────────────────────────────
cmd_export() {
    info "开始导出..."

    # 检查容器运行状态
    if ! docker compose -f "$COMPOSE_FILE" ps db | grep -qE "Up|running"; then
        error "db 容器未运行，请先执行 docker compose up -d"
    fi

    # 导出数据库
    info "导出 PostgreSQL 数据库 → $BACKUP_DB"
    docker compose -f "$COMPOSE_FILE" exec -T db \
        pg_dump -U changeit docdokuplm > "$BACKUP_DB"
    success "数据库导出完成（$(du -sh "$BACKUP_DB" | cut -f1)）"

    # 导出文件库（vault 固定为 bind mount）
    info "导出文件库 → $BACKUP_VAULT"
    if [ -d "$SCRIPT_DIR/data/vault" ]; then
        tar czf "$BACKUP_VAULT" -C "$SCRIPT_DIR/data" vault
    else
        error "找不到 ./data/vault，请确认服务已至少启动过一次"
    fi
    success "文件库导出完成（$(du -sh "$BACKUP_VAULT" | cut -f1)）"

    echo ""
    success "导出完成！请将以下两个文件复制到新机器："
    echo "  $BACKUP_DB"
    echo "  $BACKUP_VAULT"
}

# ─────────────────────────────────────────────
# import：导入数据库和文件库
# ─────────────────────────────────────────────
cmd_import() {
    info "开始导入..."

    [ -f "$BACKUP_DB" ]    || error "找不到 $BACKUP_DB，请先将备份文件放到此目录"
    [ -f "$BACKUP_VAULT" ] || error "找不到 $BACKUP_VAULT，请先将备份文件放到此目录"

    # 确保 bind mount 目录存在
    mkdir -p "$SCRIPT_DIR/data/db"
    mkdir -p "$SCRIPT_DIR/data/vault"

    # 启动服务（仅 db，不启动 back 避免冲突）
    info "启动 db 容器..."
    docker compose -f "$COMPOSE_FILE" up -d db
    sleep 5  # 等待 PostgreSQL 就绪

    # 清空并导入数据库
    info "导入数据库..."
    docker compose -f "$COMPOSE_FILE" exec -T db \
        psql -U changeit -c "DROP DATABASE IF EXISTS docdokuplm;"
    docker compose -f "$COMPOSE_FILE" exec -T db \
        psql -U changeit -c "CREATE DATABASE docdokuplm;"
    docker compose -f "$COMPOSE_FILE" exec -T db \
        psql -U changeit docdokuplm < "$BACKUP_DB"
    success "数据库导入完成"

    # 导入文件库
    info "导入文件库..."
    tar xzf "$BACKUP_VAULT" -C "$SCRIPT_DIR/data"
    success "文件库导入完成"

    # 启动全部服务
    info "启动所有服务..."
    docker compose -f "$COMPOSE_FILE" up -d
    success "全部完成！服务已启动。"
}

# ─────────────────────────────────────────────
# from-volumes：旧 named volume vault → bind mount（一次性）
# db 始终使用 named volume，无需迁移。
# ─────────────────────────────────────────────
cmd_from_volumes() {
    warn "此操作将把旧 docdoku-plm-server-volume 中的文件复制到 ./data/vault/，只需运行一次。"
    read -rp "确认继续？[y/N] " confirm
    [[ "$confirm" =~ ^[yY]$ ]] || { info "已取消。"; exit 0; }

    COMPOSE_PROJECT=$(basename "$SCRIPT_DIR")

    if ! docker volume ls | grep -q "${COMPOSE_PROJECT}_docdoku-plm-server-volume"; then
        error "找不到旧 named volume ${COMPOSE_PROJECT}_docdoku-plm-server-volume，可能已经迁移过了"
    fi

    info "停止服务..."
    docker compose -f "$COMPOSE_FILE" down

    mkdir -p "$SCRIPT_DIR/data/vault"

    info "迁移文件库..."
    docker run --rm \
        -v "${COMPOSE_PROJECT}_docdoku-plm-server-volume:/src" \
        -v "$SCRIPT_DIR/data/vault:/dst" \
        alpine sh -c "cp -a /src/. /dst/"
    success "文件库迁移完成"

    info "启动服务..."
    docker compose -f "$COMPOSE_FILE" up -d
    success "迁移完成！文件库现在保存在 ./data/vault/ 目录下。"

    warn "旧 named volume 未删除，确认服务正常后可手动删除："
    echo "  docker volume rm ${COMPOSE_PROJECT}_docdoku-plm-server-volume"
}

# ─────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────
case "${1:-}" in
    export)       cmd_export ;;
    import)       cmd_import ;;
    from-volumes) cmd_from_volumes ;;
    *)
        echo "用法: $0 {export|import|from-volumes}"
        echo ""
        echo "  export        导出数据库和文件库到备份文件"
        echo "  import        从备份文件导入数据库和文件库"
        echo "  from-volumes  一次性：将旧 named volume 迁入 ./data/"
        exit 1
        ;;
esac
