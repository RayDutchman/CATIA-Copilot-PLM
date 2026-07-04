#!/usr/bin/env bash
# build.sh — 构建 Python-only 转换服务镜像（自包含，无外部依赖）
#
# 所有构建材料均位于本目录（conversion-service-py/）：
#   - convert_step_glb.py  STEP/IGES → GLB 转换脚本
#   - convert_mesh.py      STL/PLY/OBJ/DAE/IFC → GLB 转换脚本
#   - converter.py         统一转换入口 + unaccent()
#   - main.py              Kafka 编排服务
#   - requirements.txt     Python 依赖清单
#   - install-python-deps.sh  pip 安装脚本（支持离线/内网/PyPI 三级回退）
#   - wheels/              cadquery-ocp 等离线 wheel 包（cp311 预编译）
#   - Dockerfile           Docker 构建描述
#
# 用法：
#   bash build.sh [TAG]
#   默认 TAG: docdoku/docdoku-plm-conversion-service:2.7.0-py
#
# 构建完成后直接 docker compose up -d --force-recreate --no-deps conversion

set -euo pipefail

TAG="${1:-docdoku/docdoku-plm-conversion-service:2.7.0-py}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "[build] 开始构建镜像: $TAG"
echo "[build] 构建上下文: $SCRIPT_DIR"

docker build -t "$TAG" "$SCRIPT_DIR"

echo "[build] 完成：$TAG"
