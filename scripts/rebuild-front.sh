#!/usr/bin/env bash
# rebuild-front.sh
#
# 重建前端 Docker 镜像并重新部署。
# 适用于修改以下任何文件后：
#   - app/product-structure/js/dmu/LoaderManager.js
#   - app/js/dmu/loaders/GLTFLoader.js (或其他 loader)
#   - app/js/common-objects/views/part/cad_instance_view.js
#   - 任何前端源码
#
# 脚本会自动：
#   1. 同步 app/ 中的 loader 文件到 dist/（GLTFLoader 等新增文件）
#   2. 更新 dist/ 中 index.html 的 data-main rev 参数，强制浏览器加载新版本
#   3. 重建 Docker 镜像并部署
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

# ── 1. 同步 app/js/dmu/loaders/ -> dist/js/dmu/loaders/ ──────────────────────
section "同步 loader 文件 app/ -> dist/"
SRC_LOADERS="${FRONT_DIR}/app/js/dmu/loaders"
DST_LOADERS="${FRONT_DIR}/dist/js/dmu/loaders"

for f in "${SRC_LOADERS}"/*.js; do
    fname=$(basename "$f")
    if [ ! -f "${DST_LOADERS}/${fname}" ]; then
        cp "$f" "${DST_LOADERS}/${fname}"
        info "新增: dist/js/dmu/loaders/${fname}"
    elif ! cmp -s "$f" "${DST_LOADERS}/${fname}"; then
        cp "$f" "${DST_LOADERS}/${fname}"
        info "更新: dist/js/dmu/loaders/${fname}"
    fi
done

# ── 2. 更新 index.html 中的 rev 参数，强制浏览器绕过缓存 ─────────────────────
section "更新 index.html rev 参数"
NEW_REV=$(date +%s)000

for index_html in \
    "${FRONT_DIR}/dist/visualization/index.html" \
    "${FRONT_DIR}/dist/product-structure/index.html"; do
    if [ -f "${index_html}" ]; then
        # Replace any existing rev=NNNN with new rev
        sed -i "s/main\.js?rev=[0-9]*/main.js?rev=${NEW_REV}/g" "${index_html}"
        info "Updated rev=${NEW_REV} in $(basename $(dirname ${index_html}))/index.html"
    fi
done

# Also update urlArgs in main.js files so RequireJS uses new rev for sub-modules
for main_js in \
    "${FRONT_DIR}/dist/visualization/main.js" \
    "${FRONT_DIR}/dist/product-structure/main.js"; do
    if [ -f "${main_js}" ]; then
        sed -i "s/urlArgs:\"rev=[0-9]*\"/urlArgs:\"rev=${NEW_REV}\"/g" "${main_js}"
        info "Updated urlArgs rev=${NEW_REV} in $(basename $(dirname ${main_js}))/main.js"
    fi
done

# ── 3. 构建镜像 ───────────────────────────────────────────────────────────────
section "构建前端镜像: ${IMAGE}"
cd "${FRONT_DIR}"
docker build -f docker/Dockerfile -t "${IMAGE}" . \
  || err "前端 Docker 镜像构建失败"
info "镜像构建完成"

# ── 4. 部署容器 ───────────────────────────────────────────────────────────────
section "重新部署前端容器"
cd "${DOCKER_DIR}"
docker compose up --force-recreate --no-deps -d front \
  || err "docker compose 部署失败"

sleep 3
docker ps --filter "name=${CONTAINER}" --format "  状态: {{.Status}}"
info "前端部署完成: ${IMAGE}"
echo ""
echo "  rev=${NEW_REV} 已写入 index.html 和 main.js"
echo "  浏览器会自动请求新版本，无需手动强制刷新"
