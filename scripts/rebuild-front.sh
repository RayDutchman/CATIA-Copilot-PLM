#!/usr/bin/env bash
# rebuild-front.sh
#
# 从前端源码重建 dist，构建前端镜像并重新部署。
# 适用于任何前端源码修改。
#
# 脚本会自动：
#   1. 从源码执行 npm run build，完整重建 dist/
#   2. 统一刷新所有前端入口的 rev 参数，强制浏览器加载新版本
#   3. 重建 Docker 镜像并部署
#   4. 校验容器内文件与本地 dist 是否一致
#   5. 校验 HTTP 实际返回的入口页 rev 是否一致
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

# ── 1. 从源码重建 dist/ ──────────────────────────────────────────────────────
section "从源码重建前端 dist"
cd "${FRONT_DIR}"
npm_config_legacy_peer_deps=true npm run build \
  || err "前端源码构建失败"
info "dist 重建完成"

# ── 2. 更新 index.html / main.js 中的 rev 参数，强制浏览器绕过缓存 ───────────
section "刷新所有前端入口 rev 参数"
NEW_REV=$(date +%s)000

for index_html in \
    "${FRONT_DIR}/dist/visualization/index.html" \
    "${FRONT_DIR}/dist/product-structure/index.html" \
    "${FRONT_DIR}/dist/product-management/index.html" \
    "${FRONT_DIR}/dist/parts/index.html"; do
    if [ -f "${index_html}" ]; then
        # Replace any existing rev=NNNN with new rev
        sed -i "s/main\.js?rev=[0-9]*/main.js?rev=${NEW_REV}/g" "${index_html}"
        info "Updated rev=${NEW_REV} in $(basename $(dirname ${index_html}))/index.html"
    fi
done

# Also update urlArgs in main.js files so RequireJS uses new rev for sub-modules
for main_js in \
    "${FRONT_DIR}/dist/visualization/main.js" \
    "${FRONT_DIR}/dist/product-structure/main.js" \
    "${FRONT_DIR}/dist/product-management/main.js" \
    "${FRONT_DIR}/dist/parts/main.js"; do
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

# ── 5. 校验容器内文件与本地 dist 一致 ───────────────────────────────────────
section "校验容器内文件与本地 dist 一致"
for relpath in \
    "visualization/main.js" \
    "visualization/index.html" \
    "product-structure/main.js" \
    "product-structure/index.html" \
    "product-management/main.js" \
    "product-management/index.html" \
    "parts/main.js" \
    "parts/index.html"; do
    local_sha=$(sha256sum "${FRONT_DIR}/dist/${relpath}" | awk '{print $1}')
    container_sha=$(docker exec "${CONTAINER}" sh -lc "sha256sum /usr/share/nginx/html/${relpath}" | awk '{print $1}')
    if [ "${local_sha}" != "${container_sha}" ]; then
        err "容器文件与本地 dist 不一致: ${relpath}"
    fi
    info "校验通过: ${relpath}"
done

# ── 6. 校验 HTTP 实际返回的 rev 参数 ─────────────────────────────────────────
section "校验 HTTP 实际返回的入口 rev"
for page in \
    "visualization/index.html" \
    "product-structure/index.html" \
    "product-management/index.html" \
    "parts/index.html"; do
    actual_rev=$(python3 - <<PY
import re, urllib.request
text = urllib.request.urlopen('http://localhost:8000/${page}').read().decode('utf-8', 'ignore')
match = re.search(r'data-main="main\\.js\\?([^\"]+)"', text)
print(match.group(1) if match else 'NONE')
PY
)
    if [ "${actual_rev}" != "rev=${NEW_REV}" ]; then
        err "HTTP 返回的 rev 不正确: ${page} -> ${actual_rev}"
    fi
    info "HTTP rev 正确: ${page} -> ${actual_rev}"
done

info "前端部署完成: ${IMAGE}"
echo ""
echo "  rev=${NEW_REV} 已写入所有前端入口的 index.html 和 main.js"
echo "  已校验 dist / 容器文件 / HTTP 返回三层一致"
