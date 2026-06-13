#!/usr/bin/env bash
# rebuild-front.sh
#
# 重建前端 Docker 镜像并重新部署。
# 适用于修改以下任何文件后：
#   - app/product-structure/js/dmu/LoaderManager.js
#   - app/js/dmu/loaders/GLTFLoader.js (或其他 loader)
#   - app/js/common-objects/views/part/cad_instance_view.js
#   - dist/ 目录下任何 minified 文件
#   - 任何前端源码
#
# 用法：
#   bash scripts/rebuild-front.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
FRONT_DIR="${REPO_ROOT}/docdoku-plm-front"
DOCKER_DIR="${REPO_ROOT}/docdoku-plm-docker"
IMAGE="docdoku/docdoku-plm-front:2.6.2"
CONTAINER="docdoku-plm-docker-front-1"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[✓]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*"; }
err()     { echo -e "${RED}[✗]${NC} $*" >&2; exit 1; }
section() { echo -e "\n${GREEN}══ $* ══${NC}"; }

section "构建前端镜像: ${IMAGE}"
cd "${FRONT_DIR}"
docker build -f docker/Dockerfile -t "${IMAGE}" . \
  || err "前端 Docker 镜像构建失败"
info "镜像构建完成"

section "重新部署前端容器"
cd "${DOCKER_DIR}"
docker compose up --force-recreate --no-deps -d front \
  || err "docker compose 部署失败"

sleep 3
docker ps --filter "name=${CONTAINER}" --format "  状态: {{.Status}}"
info "前端部署完成: ${IMAGE}"
echo ""
echo "  注意：浏览器需要强制刷新（Ctrl+Shift+R）才能加载新版前端资源"
