#!/bin/bash
# 前端热更新开发服务器启动脚本
# 用法：./dev.sh
# 效果：http://localhost:9001  浏览器实时刷新（文件改动后约 1-2 秒）
# 后端：指向 Docker back-py http://localhost:8009

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 激活 Node 14（Grunt 兼容版本）
export NVM_DIR="$HOME/.nvm"
source "$NVM_DIR/nvm.sh" 2>/dev/null
nvm use 14 --silent 2>/dev/null || nvm use 14

echo "[dev] Starting PLM frontend dev server on http://localhost:9001"
echo "[dev] API backend: http://localhost:8009 (Docker back-py)"
echo "[dev] Edit files in app/ — browser will auto-reload"
echo "[dev] Ctrl+C to stop"
echo ""

exec ./node_modules/.bin/grunt serve
