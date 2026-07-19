# 一键部署脚本整理 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 整理仓库中散落的多个构建/部署脚本，提供一个清晰的根目录 `setup.sh` 作为技术用户的一键入口，同时删除过时的 Payara 相关脚本和 sample-data 目录。

**Architecture:** 根目录新增 `setup.sh` 提供 build/up/down/status/logs 五个子命令，内部调用整理后的 `setup/` 目录子脚本；`docdoku-plm-docker/start.sh` 和 `start-services.sh` 更新以去掉 Payara 检查；删除 `docdoku-plm-sample-data/` 和三个 Payara 相关脚本。

**Tech Stack:** Bash, Docker Compose, Node.js 14 (nvm), docker buildkit

## Global Constraints

- `setup.sh` 必须在 bash（非 sh）下运行（`#!/usr/bin/env bash`）
- 所有脚本使用 `set -euo pipefail`
- 路径全部使用 `$REPO_ROOT`（脚本自身相对路径推导），不硬编码 `/home/chenweibo`
- 镜像 tag 常量：front=`docdoku/docdoku-plm-front:2.6.2`，back-py=`docdoku-plm-docker-back-py:latest`，conversion=`docdoku/docdoku-plm-conversion-service:2.7.0-py`
- Node.js 版本：14（优先 nvm，fallback 到系统 node）
- Docker Compose 命令统一用 `docker compose`（v2），compose 文件在 `$REPO_ROOT/docdoku-plm-docker/`
- Payara (`back`) 不出现在任何新/改脚本的启动逻辑中（保留在 docker-compose.yml 作为 `restart: "no"` 供本地对比）

---

### Task 1：删除废弃文件和目录

**Files:**
- Delete: `docdoku-plm-sample-data/`（整个目录）
- Delete: `scripts/build-base-image.sh`
- Delete: `scripts/build-backend-full.sh`
- Delete: `scripts/rebuild-conversion-service.sh`

**Interfaces:**
- Produces: 仓库无 Payara 构建脚本和 sample-data，后续 setup.sh 无需引用它们

- [ ] **Step 1: 删除废弃文件**

```bash
git rm -r docdoku-plm-sample-data/
git rm scripts/build-base-image.sh scripts/build-backend-full.sh scripts/rebuild-conversion-service.sh
```

- [ ] **Step 2: 验证删除结果**

```bash
ls docdoku-plm-sample-data/ 2>/dev/null && echo "FAIL: still exists" || echo "OK: deleted"
ls scripts/
# 预期只剩：build-i18n.sh  rebuild-front.sh
```

- [ ] **Step 3: Commit**

```bash
git commit -m "chore: remove sample-data and Payara build scripts"
```

---

### Task 2：更新 `docdoku-plm-docker/start.sh`（去掉 Payara 镜像检查）

**Files:**
- Modify: `docdoku-plm-docker/start.sh`

**Interfaces:**
- Consumes: 现有 `start.sh` 内容（检查三个镜像：server/front/conversion-service:2.6.2）
- Produces: 只检查两个镜像（front + back-py），且 conversion 由 compose 自动 build

- [ ] **Step 1: 读取当前内容**

```bash
cat docdoku-plm-docker/start.sh
```

- [ ] **Step 2: 替换镜像检查逻辑**

将 `start.sh` 中的镜像检查段落替换为：

```bash
# ── 前置检查：确认私有镜像已构建 ──────────────────────────────
MISSING=""
for img in \
    "docdoku/docdoku-plm-front:2.6.2" \
    "docdoku-plm-docker-back-py:latest"; do
    if ! docker image inspect "$img" > /dev/null 2>&1; then
        MISSING="$MISSING\n  - $img"
    fi
done

if [ -n "$MISSING" ]; then
    echo ""
    echo "❌ 以下镜像尚未构建，无法启动：$MISSING"
    echo ""
    echo "请先在仓库根目录执行：  ./setup.sh build"
    echo ""
    exit 1
fi
```

并将错误提示中的 README 步骤改为 `./setup.sh build`，删除 Payara 相关步骤说明。

- [ ] **Step 3: 验证脚本语法**

```bash
bash -n docdoku-plm-docker/start.sh && echo "syntax OK"
```

- [ ] **Step 4: 更新 start-services.sh 中的 Payara 注释**

`docdoku-plm-docker/start-services.sh` 第一行注释已正确（跳过 back），无需修改逻辑，但检查是否有硬编码路径：

```bash
head -5 docdoku-plm-docker/start-services.sh
# 若有 "cd /home/chenweibo/..." → 替换为：
# SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# cd "$SCRIPT_DIR"
```

- [ ] **Step 5: Commit**

```bash
git add docdoku-plm-docker/start.sh docdoku-plm-docker/start-services.sh
git commit -m "chore: remove Payara image check from start.sh, use relative paths"
```

---

### Task 3：创建 `setup/build-images.sh`

**Files:**
- Create: `setup/build-images.sh`

**Interfaces:**
- Consumes: `$REPO_ROOT`（由调用方 export）；`scripts/rebuild-front.sh` 的逻辑（npm build + docker build front）
- Produces: 三个镜像构建完成，退出码 0

- [ ] **Step 1: 创建 `setup/` 目录**

```bash
mkdir -p setup
```

- [ ] **Step 2: 写 `setup/build-images.sh`**

```bash
cat > setup/build-images.sh << 'SCRIPT'
#!/usr/bin/env bash
# setup/build-images.sh — 构建 front / back-py / conversion 三个镜像
# 由 setup.sh build 调用，不直接运行
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

echo "=== [1/3] 构建前端镜像 ==="
# 检测 Node 14
NODE_CMD=""
if command -v nvm &>/dev/null || [ -s "$HOME/.nvm/nvm.sh" ]; then
    export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
    [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
    nvm use 14 2>/dev/null || nvm install 14
    NODE_CMD="node"
elif node --version 2>/dev/null | grep -q "^v14\."; then
    NODE_CMD="node"
else
    echo "❌ 需要 Node.js 14（nvm 或系统安装）。请先安装：nvm install 14" >&2
    exit 1
fi

cd "$REPO_ROOT/docdoku-plm-front"
npm_config_legacy_peer_deps=true npm run build
docker build -f docker/Dockerfile -t docdoku/docdoku-plm-front:2.6.2 .
echo "✅ front 镜像构建完成"

echo "=== [2/3] 构建 back-py 镜像 ==="
cd "$REPO_ROOT/docdoku-plm-server-py"
docker build -t docdoku-plm-docker-back-py:latest .
echo "✅ back-py 镜像构建完成"

echo "=== [3/3] 构建 conversion 镜像 ==="
cd "$REPO_ROOT/conversion-service-py"
docker build -t docdoku/docdoku-plm-conversion-service:2.7.0-py .
echo "✅ conversion 镜像构建完成"

echo ""
echo "所有镜像构建完成。现在可以运行：./setup.sh up"
SCRIPT
chmod +x setup/build-images.sh
```

- [ ] **Step 3: 验证语法**

```bash
bash -n setup/build-images.sh && echo "syntax OK"
```

- [ ] **Step 4: Commit**

```bash
git add setup/build-images.sh
git commit -m "feat(setup): add setup/build-images.sh for front/back-py/conversion"
```

---

### Task 4：创建根目录 `setup.sh`

**Files:**
- Create: `setup.sh`

**Interfaces:**
- Consumes: `setup/build-images.sh`（Task 3），`docdoku-plm-docker/start-services.sh`，`docdoku-plm-docker/`（compose 工作目录）
- Produces: 统一入口，支持 build/up/down/status/logs/help 子命令

- [ ] **Step 1: 写 `setup.sh`**

```bash
cat > setup.sh << 'SCRIPT'
#!/usr/bin/env bash
# setup.sh — CATIA-Copilot-PLM 部署入口
#
# 用法：
#   ./setup.sh build         构建所有镜像（front / back-py / conversion）
#   ./setup.sh up            启动所有服务
#   ./setup.sh down          停止所有服务
#   ./setup.sh status        查看容器状态
#   ./setup.sh logs [svc]    查看日志（默认 back-py）
#   ./setup.sh help          显示此帮助
#
# 前置依赖：
#   - Docker Engine 24+（含 docker compose v2）
#   - Node.js 14（通过 nvm 或系统安装，仅 build 时需要）
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
        # 检查镜像
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
                echo "   注册账号后，执行以下命令提权为管理员（将 <login> 替换为你的登录名）："
                echo "   docker exec docdoku-plm-docker-db-1 psql -U changeit -d docdokuplm \\"
                echo "     -c \"INSERT INTO usergroupmapping (login, groupname) VALUES ('<login>', 'admin') ON CONFLICT DO NOTHING;\""
                exit 0
            fi
            echo "  [${i}/12] 等待中..."
            sleep 5
        done
        echo "⚠️  服务启动超时，请用 ./setup.sh logs 查看日志"
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
    help|--help|-h)
        head -13 "${BASH_SOURCE[0]}" | grep "^#" | sed 's/^# //' | sed 's/^#//'
        ;;
    *)
        echo "未知命令：$cmd，运行 ./setup.sh help 查看帮助" >&2
        exit 1
        ;;
esac
SCRIPT
chmod +x setup.sh
```

- [ ] **Step 2: 验证语法**

```bash
bash -n setup.sh && echo "syntax OK"
./setup.sh help
# 预期输出：usage 说明
```

- [ ] **Step 3: 验证 status 子命令**

```bash
./setup.sh status
# 预期：docker compose ps 输出
```

- [ ] **Step 4: Commit**

```bash
git add setup.sh
git commit -m "feat: add root-level setup.sh with build/up/down/status/logs commands"
```

---

### Task 5：更新 README.md

**Files:**
- Modify: `README.md`（根目录）

**Interfaces:**
- Consumes: `setup.sh` 的命令接口（Task 4）
- Produces: README 首次部署章节简化为 3 步

- [ ] **Step 1: 读取 README 的首次部署章节**

```bash
grep -n "首次部署\|Step\|步骤\|build\|setup" README.md | head -30
```

- [ ] **Step 2: 将首次部署流程更新为**

找到原有 "首次部署流程" 章节，替换内容为：

```markdown
## 首次部署

**前置依赖：**
- Docker Engine 24+（含 `docker compose` v2）
- Node.js 14（推荐通过 [nvm](https://github.com/nvm-sh/nvm) 安装：`nvm install 14`）

**步骤：**

```bash
# 1. 克隆仓库
git clone https://github.com/RayDutchman/CATIA-Copilot-PLM.git
cd CATIA-Copilot-PLM

# 2. 构建所有镜像（约 5-10 分钟）
./setup.sh build

# 3. 启动服务
./setup.sh up
```

服务就绪后访问 `http://localhost:8000`，注册账号后执行提权命令即可使用：

```bash
docker exec docdoku-plm-docker-db-1 psql -U changeit -d docdokuplm \
  -c "INSERT INTO usergroupmapping (login, groupname) VALUES ('<your-login>', 'admin') ON CONFLICT DO NOTHING;"
```

**日常命令：**

| 命令 | 说明 |
|------|------|
| `./setup.sh up` | 启动服务 |
| `./setup.sh down` | 停止服务 |
| `./setup.sh status` | 查看容器状态 |
| `./setup.sh logs [服务名]` | 查看日志（默认 back-py） |
| `./setup.sh build` | 重建所有镜像 |

**数据迁移（跨机器）：**

```bash
# 旧机器导出
cd docdoku-plm-docker && bash migrate.sh export

# 新机器导入（先 git clone + ./setup.sh build）
cd docdoku-plm-docker && bash migrate.sh import
```
```

- [ ] **Step 3: 验证 README 格式**

```bash
# 确认 markdown 基本结构完整
grep "^## " README.md
```

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: simplify first-deploy flow to 3 steps using setup.sh"
```

---

### Task 6：端到端验证

**Files:** 无新文件

- [ ] **Step 1: 验证 setup.sh build 不报错（dry-run 检查）**

```bash
bash -n setup.sh && echo "setup.sh syntax OK"
bash -n setup/build-images.sh && echo "build-images.sh syntax OK"
bash -n docdoku-plm-docker/start.sh && echo "start.sh syntax OK"
bash -n docdoku-plm-docker/start-services.sh && echo "start-services.sh syntax OK"
```

- [ ] **Step 2: 验证 setup.sh help 输出**

```bash
./setup.sh help
# 预期：显示用法说明，退出码 0
```

- [ ] **Step 3: 验证 setup.sh status 在服务运行时正常**

```bash
./setup.sh status
# 预期：docker compose ps 输出，front/back-py 等容器 Up
```

- [ ] **Step 4: 验证 setup.sh logs 带服务名**

```bash
timeout 3 ./setup.sh logs front || true
# 预期：输出 front 容器日志后超时退出（正常）
```

- [ ] **Step 5: Final commit**

```bash
git add -A
git status  # 确认只有预期文件
git commit -m "chore: deployment scripts cleanup and setup.sh integration" 2>/dev/null || echo "nothing to commit"
git push origin main
```

---

## 文件变更汇总

| 操作 | 文件 |
|------|------|
| 删除 | `docdoku-plm-sample-data/`（整个目录） |
| 删除 | `scripts/build-base-image.sh` |
| 删除 | `scripts/build-backend-full.sh` |
| 删除 | `scripts/rebuild-conversion-service.sh` |
| 修改 | `docdoku-plm-docker/start.sh`（去掉 Payara 镜像检查） |
| 修改 | `docdoku-plm-docker/start-services.sh`（去掉硬编码路径，若有） |
| 新增 | `setup/build-images.sh` |
| 新增 | `setup.sh` |
| 修改 | `README.md`（首次部署章节） |

## 保留不变（供本地 Payara 对比用）

- `docdoku-plm-server/`（Java 后端源码）
- `docdoku-plm-docker/docker-compose.yml` 中的 `back` service（`restart: "no"`）
- `scripts/rebuild-front.sh`、`scripts/build-i18n.sh`（日常开发脚本）
