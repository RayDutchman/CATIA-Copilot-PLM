#!/usr/bin/env bash
# rebuild-conversion-service.sh
#
# 从源码重建 docdoku-plm-conversion-service 镜像并重新部署容器。
# 适用于修改以下任何文件后：
#   - convert_step_glb.py
#   - convert_step_obj.py (已废弃，保留兼容)
#   - StepFileConverterImpl.java
#   - 任何 conversion-service 源码
#   - Dockerfile.jvm
#
# 用法：
#   bash scripts/rebuild-conversion-service.sh           # 完整重建（默认）
#   bash scripts/rebuild-conversion-service.sh --fast    # 只重新打包 jar，跳过 Docker 层缓存重建
#   bash scripts/rebuild-conversion-service.sh --deploy-only  # 只重新部署（jar 已在容器内热替换）
#
# 前提：
#   - Docker 已运行，docker compose 可用
#   - Maven 已安装（mvn 在 PATH 中）
#   - 当前目录或 REPO_ROOT 指向项目根目录

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONV_DIR="${REPO_ROOT}/docdoku-plm-conversion-service"
DOCKER_DIR="${REPO_ROOT}/docdoku-plm-docker"
IMAGE="docdoku/docdoku-plm-conversion-service:2.6.2"
CONTAINER="docdoku-plm-docker-conversion-1"

# ── 颜色输出 ──────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[✓]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*"; }
err()     { echo -e "${RED}[✗]${NC} $*" >&2; exit 1; }
section() { echo -e "\n${GREEN}══ $* ══${NC}"; }

FAST=false
DEPLOY_ONLY=false
for arg in "$@"; do
  case "$arg" in
    --fast)        FAST=true ;;
    --deploy-only) DEPLOY_ONLY=true ;;
    *) err "未知参数: $arg（支持 --fast / --deploy-only）" ;;
  esac
done

# ── 1. Maven 构建 ──────────────────────────────────────────────────────────
if ! $DEPLOY_ONLY; then
  section "Maven 构建 conversion-service"

  # conversion-service 依赖 docdoku-plm-api-java，先确认本地仓库有
  API_JAR="${HOME}/.m2/repository/com/docdoku/plm/docdoku-plm-api-java/2.6.2/docdoku-plm-api-java-2.6.2.jar"
  if [ ! -f "${API_JAR}" ]; then
    warn "本地 Maven 仓库缺少 docdoku-plm-api-java，先构建 API 模块（约 3-5 分钟）..."
    cd "${REPO_ROOT}/docdoku-plm-api"
    mvn install -DskipTests -pl docdoku-plm-api-base,docdoku-plm-api-java --also-make -q \
      || err "docdoku-plm-api 构建失败"
    info "API 模块构建完成"
  fi

  cd "${CONV_DIR}"
  info "打包 conversion-service jar..."
  mvn package -DskipTests -q \
    || err "Maven 构建失败，查看上方输出"

  RUNNER_JAR="${CONV_DIR}/conversion-service/target/conversion-service-2.6.2-runner.jar"
  [ -f "${RUNNER_JAR}" ] || err "未找到 runner.jar: ${RUNNER_JAR}"
  info "jar 构建完成: $(du -sh ${RUNNER_JAR} | cut -f1)"
fi

# ── 2. Docker 镜像构建 ──────────────────────────────────────────────────────
if ! $DEPLOY_ONLY; then
  section "构建 Docker 镜像: ${IMAGE}"

  cd "${CONV_DIR}"

  if $FAST; then
    # --fast 模式：只替换 jar，不重建整个镜像（适合 Python 脚本没变时）
    warn "--fast 模式：直接热替换容器内 jar（跳过镜像重建）"
    RUNNER_JAR="${CONV_DIR}/conversion-service/target/conversion-service-2.6.2-runner.jar"
    docker stop "${CONTAINER}" 2>/dev/null || true
    docker cp "${RUNNER_JAR}" "${CONTAINER}:/deployments/app.jar" \
      || err "复制 jar 到容器失败（容器可能不存在，改用完整模式）"
    docker start "${CONTAINER}"
    info "jar 热替换完成，容器已重启"
  else
    # 完整重建镜像（Python 脚本或 Dockerfile 有变化时必须）
    info "开始构建镜像（首次约 5-10 分钟，后续利用缓存约 1 分钟）..."
    docker build -f Dockerfile.jvm -t "${IMAGE}" . \
      || err "Docker 镜像构建失败"
    info "镜像构建完成: ${IMAGE}"
  fi
fi

# ── 3. 重新部署容器 ──────────────────────────────────────────────────────────
if ! $FAST; then
  section "重新部署容器"
  cd "${DOCKER_DIR}"
  docker compose up --force-recreate --no-deps -d conversion \
    || err "docker compose 部署失败"
fi

# ── 4. 等待服务就绪 ──────────────────────────────────────────────────────────
section "等待转换服务就绪"
MAX_WAIT=60
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
  if docker logs "${CONTAINER}" 2>&1 | grep -q "Successfully joined group"; then
    info "转换服务已就绪，Kafka 连接正常"
    break
  fi
  sleep 2
  ELAPSED=$((ELAPSED + 2))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
  warn "等待超时（${MAX_WAIT}s），请手动检查: docker logs ${CONTAINER}"
else
  echo ""
  echo -e "${GREEN}✓ 部署完成${NC}"
  echo "  镜像:    ${IMAGE}"
  echo "  容器:    ${CONTAINER}"
  docker ps --filter "name=${CONTAINER}" --format "  状态:    {{.Status}}"
  echo ""
  echo "  后续提示："
  echo "  - 修改 convert_step_glb.py 后：bash scripts/rebuild-conversion-service.sh"
  echo "  - 只改了 Java 代码（未改 Dockerfile/wheels）：bash scripts/rebuild-conversion-service.sh --fast"
  echo "  - 查看实时日志：docker logs -f ${CONTAINER}"
fi
