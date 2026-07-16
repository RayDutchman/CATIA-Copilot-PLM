# CATIA-Copilot-PLM 项目指令

本项目是基于 DocDoku PLM 2.6.2 的二次开发版，面向 CATIA 协同设计场景。遇到不确定的问题，优先查阅 `docs/` 目录下对应文档，而不是凭印象处理。

---

## ⚠️ 强制规则：会话工作流

### 会话开始时
1. 读取 `docs/REMINDERS.md`，了解当前待办和已知阻塞
2. 如果任务涉及已知问题，优先参考 REMINDERS 中的上下文

### 会话收尾时（完成任务后）
必须执行以下操作，**不得跳过**：
1. **更新 `docs/CHANGELOG.md`**：在顶部添加当天日期条目，记录所有变更（feat/fix/chore/docs 前缀）
2. **更新 `docs/REMINDERS.md`**：
   - 将已解决的问题从"待办"移到"已解决"
   - 添加新发现的待办/阻塞
3. **更新相关 `docs/` 文档**：如果修改了架构、修复了 bug、变更了配置，同步更新对应文档

### 何时更新哪个文档

| 触发条件 | 必须更新的文档 |
|----------|---------------|
| 修复了 bug | `CHANGELOG.md` + `docs/issues/known-issues.md` + `REMINDERS.md` |
| 修改了容器配置/架构 | `CHANGELOG.md` + `docs/architecture/containers.md` |
| 修改了 CAD 转换流程 | `CHANGELOG.md` + `docs/architecture/3d-visualization.md` |
| 新增/变更 REST API | `CHANGELOG.md` + `docs/reference/rest-api.md` |
| 发现新的待办/阻塞 | `REMINDERS.md` |
| 任务完成 | `CHANGELOG.md` + `REMINDERS.md`（标记已解决） |

---

## 项目结构速览

| 目录 | 说明 |
|------|------|
| `docdoku-plm-server/` | 后端 Java EE 源码（Payara 5），可修改并重新构建镜像 |
| `docdoku-plm-front/` | 前端源码（Backbone.js），可修改并重新构建镜像 |
| `docdoku-plm-conversion-service/` | CAD 转换服务源码，可修改 |
| `docdoku-plm-docker/` | Docker Compose 编排文件、env 配置、vault 数据 |
| `docdoku-plm-api/` | REST API 客户端 SDK（Java） |
| `docs/` | 项目文档（架构、已知问题、运维参考） |

**重要路径**：
- vault（CAD 文件 + GLB）：`docdoku-plm-docker/data/vault/`
- 后端关键类：`docdoku-plm-server/docdoku-plm-server-ejb/src/main/java/com/docdoku/plm/server/`
- Docker 环境变量：`docdoku-plm-docker/env/`

---

## 容器架构速查

| 端口 | 容器 | 职责 |
|------|------|------|
| 8000 | `front` | Web 前端（Nginx + Backbone.js SPA） |
| 8001 | `back` | REST API（Payara 5，Java EE 8，核心服务） |
| 8002 | `kibana` | Elasticsearch 可视化（运维用） |
| 8003 | `smtp` | MailHog 邮件调试 |
| 8004 | `adminer` | PostgreSQL Web 管理 |
| 5432 | `db` | PostgreSQL 13（数据库名：`docdokuplm`，用户：`changeit`） |
| 9000 | `ssl-proxy` | HTTPS 反向代理（Nginx） |
| — | `conversion` | CAD 转换服务（消费 Kafka，STEP→GLB） |
| — | `kafka` | 消息队列（topic: `CONVERT`） |
| — | `zookeeper` | Kafka 协调服务 |
| — | `es` | Elasticsearch 6.6.1（全文搜索） |

完整说明见 `docs/architecture/containers.md`。

---

## 构建与部署

### 重建后端

```bash
cd docdoku-plm-server
mvn clean install -DskipTests
docker build --build-arg VERSION=2.6.2 -f docker/Dockerfile -t docdoku/docdoku-plm-server:2.6.2 .
cd ../docdoku-plm-docker
docker compose up -d --force-recreate --no-deps back
```

**注意**：back 容器每次重启后，Payara 的 JVM 参数（如 `-Xmx4g`）需要**再重启一次**才真正生效。第一次重启把参数写入 `domain.xml`，第二次才以新参数启动。

### 重建前端

```bash
cd docdoku-plm-front
nvm use 14 && npm run build
docker build -f docker/Dockerfile -t docdoku/docdoku-plm-front:2.6.2 .
cd ../docdoku-plm-docker
docker compose up -d --force-recreate --no-deps front
```

### 重建转换服务

```bash
# 转换服务源码在 docdoku-plm-conversion-service/，有 Dockerfile，可以修改后重建
cd docdoku-plm-conversion-service
docker build -t docdoku/docdoku-plm-conversion-service:2.6.2 .
cd ../docdoku-plm-docker
docker compose up -d --force-recreate --no-deps conversion
```

### 重建 FastAPI 后端（back-py）

```bash
cd docdoku-plm-server-py
docker build -t docdoku-plm-docker-back-py:latest .
cd ../docdoku-plm-docker
docker compose up -d --force-recreate --no-deps back-py
```

> **⚠️ 纠正一个流传的误区**："back-py 不能 rebuild、只能 docker cp" 是**错误**的。
> - 真相：**Docker 镜像仓库**（`dockerhub.timeweb.cloud`）不通，但 **pip(PyPI) 在容器内可正常访问**，基础镜像 `python:3.11-slim-bookworm` 已本地缓存。
> - 之前 build 失败的唯一原因：Dockerfile 曾 pin `python:3.11-slim`（本地无此 tag → 去坏掉的 mirror 拉 metadata 失败）。已改为本地已缓存的 `python:3.11-slim-bookworm`，`docker build` 完整通过。
> - **正常改代码后请用上面的 rebuild 流程**（更干净、可复现）。`docker cp` + `docker restart docdoku-plm-docker-back-py-1` 仅作为快速热修的权宜手段。

---

## 数据库

- 连接：`postgresql://changeit:changeit@localhost:5432/docdokuplm`
- MCP postgres 工具可直接查询（`postgres_query`）
- 主要业务表：`account`、`credential`（密码 MD5 hash）、`partmaster`、`partrevision`、`partiteration`、`conversion`、`partusagelink`

---

## 已修复的关键 Bug（勿重复踩坑）

### 1. conversion race condition（`ConverterBean.java`）

**位置**：`docdoku-plm-server-ejb/.../ConverterBean.java` → `handleConversionResultCallback`

**问题**：原代码用 `partRevision.getLastIteration()` 找要写入的 iteration，快速连续上传时会写错 iteration，导致旧 iteration 永远 `pending=true`。

**修复**：改用 `conversionDAO.findPendingConversionForRevision(partRevision)` 查找真正 pending 的 iteration。

### 2. 空几何体转换失败（`ConverterBean.java`）

**问题**：STEP 文件不含实体（如运动学约束件）时，转换器报 `no geometry generated`，后端写 `succeed=false`，前端显示错误图标。

**修复**：在 errorOutput 判断中检测 `no geometry generated`，改为 `endConversion(key, true)` 标记成功跳过。

### 3. 装配结构 amount=0（`sync.py`）

**位置**：`D:\CATIA_Related\CATIA-Copilot\catia_copilot\plm\sync.py` → `_sync_node()` 约第 1110 行

**问题**：构建 `comp_entry` 时缺少 `"amount"` 字段，Java int 默认值为 0，导致前端结构树无 `+` 号。

**修复**：已加 `"amount": len(child.instances) if child.instances else 1`。

### 4. Payara JVM 参数需两次重启

`asadmin.commands` 里的 `create-jvm-options` 修改 JVM 参数后，当次启动不立即生效，需要再重启一次容器。

### 5. WSL mirrored 网络重启后端口失效

重启电脑后 Docker 端口（8000/8001 等）可能在 Windows 侧不可访问，执行 `wsl --shutdown` 再重新启动 WSL 可恢复。

---

## CAD 转换流程

```
用户上传 .stp
→ back 写 vault + 创建 Conversion(pending=true) + 发 Kafka
→ conversion 服务消费 Kafka → STEP→GLB → PUT /api/.../conversion 回调
→ back handleConversionResultCallback → 查 pending Conversion → 写 GLB 到 vault + 更新 DB
→ 前端显示 3D 预览
```

- GLB 文件路径：`vault/Workspace_X/parts/{partNumber}/{version}/{iteration}/`
- Decimation（减面）一直失败（`code=1 read error`），这是已知问题，**不影响 GLB 生成**，无需处理

---

## CATIA Copilot 工具路径规范（Windows Python 项目）

**项目位置**：`D:\CATIA_Related\CATIA-Copilot\`（WSL 路径：`/mnt/d/CATIA_Related/CATIA-Copilot/`）

- 项目运行在 **Windows Python 3.13**，路径是 `WindowsPath`，形如 `D:\foo\bar.CATPart`
- WSL 中看到的 `/mnt/d/...` 是映射路径，**不是运行时路径**，不要传给 COM 接口
- **不要**对 Windows 路径调用 WSL 的 `Path.resolve()`
- 文件查找/过滤用 `.lower()` 大小写不敏感
- `docs.Open(file_path)` 直接传原始 Windows 路径字符串

---

## 文档索引（遇到深层问题时查阅）

| 问题类型 | 文档 |
|----------|------|
| 容器架构、端口、数据卷 | `docs/architecture/containers.md` |
| 3D 预览 / CAD 转换机制 | `docs/architecture/3d-visualization.md` |
| 装配体位置信息 / cadInstances | `docs/architecture/assembly-position.md` |
| 数据管理、vault 结构 | `docs/architecture/data-management.md` |
| 已知 Bug 追踪 | `docs/issues/known-issues.md` |
| REST API 参考 | `docs/reference/rest-api.md` |
| 认证与账号 | `docs/reference/auth-and-accounts.md` |
| 部署指南 | `docs/setup/deployment-wsl2-docker.md` |
