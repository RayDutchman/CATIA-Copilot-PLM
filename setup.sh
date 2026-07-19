#!/usr/bin/env bash
# setup.sh — CATIA-Copilot-PLM 部署入口
#
# 用法：
#   ./setup.sh build           构建所有镜像（front / back-py / conversion）约 5-10 分钟
#   ./setup.sh up              启动所有服务
#   ./setup.sh down            停止所有服务
#   ./setup.sh status          查看容器状态
#   ./setup.sh logs [服务名]   查看日志（默认 back-py）
#   ./setup.sh help            显示此帮助
#
# 前置依赖：
#   - Docker Engine 24+（含 docker compose v2）
#   - Node.js 14（nvm 或系统安装，仅 build 时需要）
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$REPO_ROOT/docdoku-plm-docker"
export REPO_ROOT

cmd="${1:-help}"

case "$cmd" in
    build)
        echo "=== CATIA-Copilot-PLM: 构建镜像 ==="
        bash "$REPO_ROOT/setup/build-images.sh"
        ;;

    up)
        echo "=== CATIA-Copilot-PLM: 启动服务 ==="
        for img in "docdoku/docdoku-plm-front:2.6.2" "docdoku-plm-docker-back-py:latest"; do
            if ! docker image inspect "$img" > /dev/null 2>&1; then
                echo "❌ 镜像 $img 不存在，请先运行：./setup.sh build" >&2
                exit 1
            fi
        done
        bash "$COMPOSE_DIR/start-services.sh"
        echo ""
        echo "=== 等待 back-py 就绪（最多 60s）==="
        for i in $(seq 1 12); do
            if curl -sf http://localhost:8000/docdoku-plm-server-rest/api/auth/providers > /dev/null 2>&1; then
                echo "✅ 服务就绪！"
                echo ""
                echo "   访问地址：http://localhost:8000"
                echo ""
                echo "   注册账号后，执行以下命令将账号提权为管理员（替换 <your-login>）："
                echo "   docker exec docdoku-plm-docker-db-1 psql -U changeit -d docdokuplm \\"
                echo "     -c \"INSERT INTO usergroupmapping (login, groupname) VALUES ('<your-login>', 'admin') ON CONFLICT DO NOTHING;\""
                exit 0
            fi
            echo "  [${i}/12] 等待中..."
            sleep 5
        done
        echo "⚠️  等待超时，服务可能仍在启动。用 ./setup.sh logs 查看详情。"
        ;;

    down)
        echo "=== CATIA-Copilot-PLM: 停止服务 ==="
        cd "$COMPOSE_DIR"
        docker compose down
        echo "✅ 已停止"
        ;;

    status)
        cd "$COMPOSE_DIR"
        docker compose ps
        ;;

    logs)
        svc="${2:-back-py}"
        cd "$COMPOSE_DIR"
        docker compose logs -f --tail=100 "$svc"
        ;;

    help|--help|-h|"")
        grep "^#" "${BASH_SOURCE[0]}" | head -12 | sed 's/^# //' | sed 's/^#//'
        ;;

    *)
        echo "未知命令：$cmd" >&2
        echo "运行 ./setup.sh help 查看帮助" >&2
        exit 1
        ;;
esac
