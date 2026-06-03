#!/usr/bin/env bash
# migrate.sh — DocdokuPLM 数据迁移工具
#
# 用法：
#   ./migrate.sh export            # 导出数据库 + 文件库到当前目录
#   ./migrate.sh import            # 从当前目录导入数据库 + 文件库并启动服务
#   ./migrate.sh load-images [DIR] # 从备份目录导入 Docker 镜像（默认 ../images/）
#   ./migrate.sh from-volumes      # 一次性：将旧 named volume 数据迁入 ./data/（首次切换时使用）
#
# 兼容环境：Linux / macOS / WSL2 / 任何安装了 Docker 的系统
# 说明：
#   - export/import 配合使用，用于跨机器迁移
#   - load-images 在新机器上还原镜像（无网络或私有镜像场景）
#   - from-volumes 仅在从旧版 docker-compose（named volume）升级时运行一次

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
BACKUP_DB="$SCRIPT_DIR/backup_db.sql"
BACKUP_VAULT="$SCRIPT_DIR/backup_vault.tar.gz"
DEFAULT_IMAGES_DIR="$SCRIPT_DIR/../images"

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

    # 检查容器运行状态（兼容新旧版 Docker Compose 状态输出）
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
    success "导出完成！请将以下两个文件复制到新机器的项目目录："
    echo "  $BACKUP_DB"
    echo "  $BACKUP_VAULT"
    echo ""
    info "同时记得复制整个 config/docdoku-plm-docker/ 目录和 images/all-images.tar"
}

# ─────────────────────────────────────────────
# load-images：从备份文件导入 Docker 镜像
# ─────────────────────────────────────────────
cmd_load_images() {
    IMAGES_DIR="${1:-$DEFAULT_IMAGES_DIR}"
    IMAGE_TAR="$IMAGES_DIR/all-images.tar"

    [ -f "$IMAGE_TAR" ] || error "找不到镜像文件：$IMAGE_TAR\n用法：./migrate.sh load-images /path/to/images/"

    info "导入 Docker 镜像（可能需要 5-15 分钟）..."
    docker load -i "$IMAGE_TAR"
    success "镜像导入完成"
    docker images | grep -E "docdoku|REPOSITORY"
}

# ─────────────────────────────────────────────
# import：导入数据库和文件库
# ─────────────────────────────────────────────
cmd_import() {
    info "开始导入..."

    [ -f "$BACKUP_DB" ]    || error "找不到 $BACKUP_DB，请先将备份文件放到此目录"
    [ -f "$BACKUP_VAULT" ] || error "找不到 $BACKUP_VAULT，请先将备份文件放到此目录"

    # 确保目录存在
    mkdir -p "$SCRIPT_DIR/data/vault"

    # 启动 db 容器等待就绪
    info "启动 db 容器..."
    docker compose -f "$COMPOSE_FILE" up -d db
    info "等待 PostgreSQL 就绪..."
    for i in $(seq 1 15); do
        if docker compose -f "$COMPOSE_FILE" exec -T db pg_isready -U changeit > /dev/null 2>&1; then
            break
        fi
        echo -n "."
        sleep 2
    done
    echo ""

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
    echo ""
    success "全部完成！等待 1-2 分钟后访问 http://localhost:8000"
    echo ""
    info "查看容器状态：docker compose ps"
    info "查看后端日志：docker compose logs --tail=50 back"
}

# ─────────────────────────────────────────────
# from-volumes：旧 named volume 迁入 ./data/
# ─────────────────────────────────────────────
cmd_from_volumes() {
    COMPOSE_PROJECT="docdoku-plm-docker"

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
    load-images)  cmd_load_images "${2:-}" ;;
    from-volumes) cmd_from_volumes ;;
    *)
        echo "用法: $0 {export|import|load-images|from-volumes}"
        echo ""
        echo "  export                   导出数据库和文件库到备份文件"
        echo "  import                   从备份文件导入数据库和文件库并启动服务"
        echo "  load-images [DIR]        导入 Docker 镜像（默认读取 ../images/all-images.tar）"
        echo "  from-volumes             一次性：将旧 named volume 迁入 ./data/"
        exit 1
        ;;
esac
