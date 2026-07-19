#!/usr/bin/env bash
# setup/build-images.sh — 构建 front / back-py / conversion 三个镜像
# 由 setup.sh build 调用，也可单独执行
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

# ── [1/3] 前端镜像 ──────────────────────────────────────────
echo "=== [1/3] 构建前端镜像（需要 Node.js 14）==="
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
if [ -s "$NVM_DIR/nvm.sh" ]; then
    . "$NVM_DIR/nvm.sh"
    nvm use 14 2>/dev/null || nvm install 14
elif ! node --version 2>/dev/null | grep -q "^v14\."; then
    echo "❌ 需要 Node.js 14。请安装 nvm 后执行：nvm install 14" >&2
    exit 1
fi

cd "$REPO_ROOT/docdoku-plm-front"
npm_config_legacy_peer_deps=true npm run build
docker build -f docker/Dockerfile -t docdoku/docdoku-plm-front:2.6.2 .
echo "✅ front 镜像构建完成"

# ── [2/3] back-py 镜像 ──────────────────────────────────────
echo "=== [2/3] 构建 back-py 镜像 ==="
cd "$REPO_ROOT/docdoku-plm-server-py"
docker build -t docdoku-plm-docker-back-py:latest .
echo "✅ back-py 镜像构建完成"

# ── [3/3] conversion 镜像 ───────────────────────────────────
echo "=== [3/3] 构建 conversion 镜像（首次约 5 分钟，含 OCC 离线 wheels）==="
cd "$REPO_ROOT/conversion-service-py"
docker build -t docdoku/docdoku-plm-conversion-service:2.7.0-py .
echo "✅ conversion 镜像构建完成"

echo ""
echo "所有镜像构建完成。运行 ./setup.sh up 启动服务。"
