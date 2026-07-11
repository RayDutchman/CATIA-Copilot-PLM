# 容器架构说明（当前状态）

> **更新日期**：2026-07-10 | **参考原始文档**：`containers-original.md`
>
> **重大变更**：FastAPI 后端（back-py）已接管全部 REST 端点，Payara（back）已停止且不随 compose 自动启动。

---

## 整体架构图

```
用户浏览器 / CATIA Copilot 工具 / 公网（cwbcode.ddnsto.com）
        │
        ▼
┌────────────────────────────────────────────────────────────────────┐
│  宿主机端口（WSL2 mirrored 网络，与 Windows 共享）                 │
│                                                                    │
│  :8000 (HTTP)  ─── front      (Nginx 前端 + 反向代理入口)          │
│  :9000 (HTTPS) ─── ssl-proxy  (Nginx SSL 反向代理)                 │
│  :8009 (HTTP)  ─── back-py    (FastAPI 后端，直连调试用)           │
│  :5432         ─── db         (PostgreSQL，客户端工具用)           │
│  :8003         ─── smtp       (MailHog Web UI)                     │
│  :8004         ─── adminer    (DB Web 管理)                        │
│  :11025        ─── smtp       (SMTP 协议端口)                      │
│                                                                    │
│  [停用，按需手动启] :8001 ─── back    (Payara，不再处理生产流量)   │
│  [停用，按需手动启] :8002 ─── kibana  (ES 可视化，运维专用)        │
└────────────────────────────────────────────────────────────────────┘
        │
        ▼ Docker 内部网络（容器名互访）
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│  浏览器 ──► front:80                                               │
│              │   Port 80 (生产)    所有 API 路由 ──► back-py:8000  │
│              │   Port 85 (对比调试) ──► back:8080  [已停用]        │
│              │                                                     │
│         ssl-proxy:443 ──► front:80（转发到 Port 80）               │
│                                                                    │
│  back-py ──► db:5432      (业务数据读写)                           │
│  back-py ──► es:9200      (全文搜索索引)                           │
│  back-py ──► smtp:1025    (邮件通知)                               │
│  back-py ──► kafka:9092   (发布 CAD 转换任务)                      │
│                                                                    │
│  zookeeper:2181 ◄── kafka:9092 ◄── conversion (消费 CONVERT topic) │
│                            │                                       │
│                            ▼ HTTP PUT 回调                         │
│                    back-py:8000/docdoku-plm-server-rest/api/...    │
│                                                                    │
│  kibana:5601 ──► es:9200  [按需手动启动]                           │
│  adminer:8080 ──► db:5432                                          │
└────────────────────────────────────────────────────────────────────┘
```

---

## 容器详细说明

### 1. front — 前端 Web 界面（Nginx 反向代理）

| 项目 | 内容 |
|------|------|
| 镜像 | `docdoku/docdoku-plm-front:2.6.2`（本地构建） |
| 宿主机端口 | `8000:80`（生产入口）、`8005:85`（对比调试，指向已停用的 Payara） |
| 职责 | 托管 PLM 前端静态文件（Backbone.js SPA），同时作为 **API 反向代理**将所有请求路由到 back-py |
| Nginx 路由 | Port 80：所有 `/docdoku-plm-server-rest/api/...` 全部 → `back-py:8000`；`/docdoku-plm-server-rest/ws` → `back-py:8000`（WebSocket）<br>Port 85：所有请求 → `back:8080`（Payara，已停用，仅对比调试保留） |
| 配置文件 | `env/front.json` → `/usr/share/nginx/html/webapp.properties.json`（前端 API 地址配置）<br>`front/nginx.conf` → `/etc/nginx/conf.d/default.conf`（UTF-8 支持、路由规则） |
| 构建方式 | `cd docdoku-plm-front && nvm use 14 && npm run build && docker build -f docker/Dockerfile -t docdoku/docdoku-plm-front:2.6.2 .` |

---

### 2. back-py — FastAPI 后端（当前主后端）

| 项目 | 内容 |
|------|------|
| 镜像 | `docdoku-plm-docker-back-py`（本地 `docker build`，无 DockerHub） |
| 宿主机端口 | `8009:8000` |
| 应用框架 | FastAPI + SQLAlchemy 2.0 + Pydantic v2，Python 3.11，uvicorn |
| 职责 | **全部 REST 业务逻辑**（已完整接管 Payara 的 43 个 Resource）：认证（JWT）、零件/文档/产品结构/变更管理/工作流/工作区管理、CAD 转换触发与回调处理、自定义查询执行引擎（QueryRule 树）、Excel 属性批量导入、WebSocket 实时通信 |
| API 路径 | `http://localhost:8009/docdoku-plm-server-rest/api/` |
| WebSocket | `ws://localhost:8009/docdoku-plm-server-rest/ws`（JWT 认证走首条 AUTH 消息） |
| 依赖容器 | `db`（PostgreSQL，healthy）、`kafka`（started） |
| 数据卷 | `./data/vault` → `/var/lib/docdoku/vault`（CAD 原文件 + 生成的 GLB）<br>`conversion-volume` → `/var/lib/docdoku/conversions`（转换临时目录，与 conversion 共享） |
| 认证机制 | JWT（`jose` 库），密码 MD5 hash 存储于 `credential` 表 |
| 部署方式 | `docker cp` + `docker restart`（热更新，不 rebuild 镜像） |
| 重建镜像 | `docker build -t docdoku-plm-docker-back-py:latest .`（从 `docdoku-plm-server-py/`），基础镜像 `python:3.11-slim-bookworm`（已本地缓存） |

---

### 3. conversion — CAD 文件转换服务

| 项目 | 内容 |
|------|------|
| 镜像 | `docdoku/docdoku-plm-conversion-service:2.7.0-py`（Python 版，源码在 `docdoku-plm-conversion-service/`） |
| 职责 | 监听 Kafka topic `CONVERT`，将 STEP 等 CAD 格式转换为 GLB，回调 back-py REST API |
| 转换流程 | Kafka 消费 → 读 vault `.stp` → 生成 `.glb` → `PUT /api/.../conversion` 回调 back-py |
| 回调端点 | `PUT http://back-py:8000/docdoku-plm-server-rest/api/workspaces/{ws}/parts/{pn}/versions/{ver}/conversion` |
| 依赖容器 | `kafka`（healthy）；不再依赖 `back`（已移除 depends_on） |
| 数据卷 | `./data/vault` → `/data/vault`<br>`conversion-volume` → `/data/conversions` |
| 已知问题 | Decimation 减面优化持续失败（`code=1 read error`），不影响 GLB 生成；空几何体（无实体 STEP）转换已在 back-py 中标记为 `succeed=true` |

---

### 4. db — PostgreSQL 数据库

| 项目 | 内容 |
|------|------|
| 镜像 | `postgres:13.1-alpine` |
| 宿主机端口 | `5432:5432` |
| 数据库名 | `docdokuplm` |
| 账号 | `changeit` / `changeit`（超级用户，供 back-py、adminer、MCP 直连） |
| 职责 | 存储全部业务数据：用户账号、工作区、零件/文档/版本/迭代、装配关系、工作流、查询、导入记录等 |
| 数据卷 | `db-volume`（Docker named volume，72 MiB） |
| 当前大小 | 72 MiB（含 2656 零件的 Workspace_2 + GD50 空工作区） |

---

### 5. es — Elasticsearch 全文搜索

| 项目 | 内容 |
|------|------|
| 镜像 | `docker.elastic.co/elasticsearch/elasticsearch:6.6.1` |
| 内部端口 | `9200`（HTTP），`9300`（节点间通信） |
| 职责 | 为零件、文档提供全文检索；back-py 在创建/更新迭代时自动同步索引（`IndexerManagerBean` 对应 `indexer_manager.py`） |
| 配置 | 单节点模式（`discovery.type=single-node`），JVM 堆 512m |
| 数据卷 | `es-volume`（10 MiB） |

---

### 6. kibana — ES 可视化 ⚠️ 按需手动启

| 项目 | 内容 |
|------|------|
| 镜像 | `docker.elastic.co/kibana/kibana:6.6.1` |
| 宿主机端口 | `8002:5601` |
| restart 策略 | `"no"`（不随 compose 自动启动） |
| 职责 | Elasticsearch Web 可视化，用于运维调试（查索引、执行搜索等） |
| 手动启动 | `docker compose start kibana` |

---

### 7. zookeeper — Kafka 协调服务

| 项目 | 内容 |
|------|------|
| 镜像 | `confluentinc/cp-zookeeper:7.6.1` |
| 内部端口 | `2181`（不对外暴露） |
| 职责 | Kafka 元数据管理和 broker 协调，维护 topic 配置、consumer group offset 等 |

---

### 8. kafka — 消息队列

| 项目 | 内容 |
|------|------|
| 镜像 | `confluentinc/cp-kafka:7.6.1` |
| 内部地址 | `kafka:9092` |
| 职责 | 异步传递 CAD 转换任务；back-py 上传 CAD 后发布 `ConversionOrder` 到 topic `CONVERT`，conversion 消费 |
| Topic | `CONVERT`（单 partition，replication factor 1） |

---

### 9. smtp — 邮件调试

| 项目 | 内容 |
|------|------|
| 镜像 | `mailhog/mailhog:v1.0.1` |
| 宿主机端口 | `11025:1025`（SMTP）、`8003:8025`（Web UI） |
| 职责 | 拦截系统邮件（工作流通知等），在 `:8003` Web 界面展示，不真正发送 |

---

### 10. adminer — 数据库管理

| 项目 | 内容 |
|------|------|
| 镜像 | `adminer:4.8.1` |
| 宿主机端口 | `8004:8080` |
| 职责 | PostgreSQL Web 管理界面，运维/调试用 |
| 登录 | 服务器 `db`，数据库 `docdokuplm`，用户/密码均为 `changeit` |

---

### 11. ssl-proxy — HTTPS 反向代理

| 项目 | 内容 |
|------|------|
| 镜像 | `nginx:1.19.1-alpine` |
| 宿主机端口 | `9000:443` |
| 职责 | HTTPS 入口，将所有请求代理到 front（含 API、WebSocket），SSL 终止 |
| 证书 | 自签名，位于 `proxy/ssl/`，domain `docdokuplm.local` |

---

### 12. back — Payara 后端 ⛔ 已停用，不自动启

| 项目 | 内容 |
|------|------|
| 镜像 | `docdoku/docdoku-plm-server:2.6.2`（本地构建，依赖 base 镜像） |
| 宿主机端口 | `8001:8080`（不自动启，端口不占用） |
| restart 策略 | `"no"`（不随 compose 自动启动） |
| 生产流量 | **无**——front nginx Port 80 全部路由到 back-py；仅 Port 85（对比端口）指向此服务 |
| 保留原因 | 应急回滚参考、端口 85 调试对比；镜像保留，数据卷共享配置保留 |
| 手动启动 | `docker compose start back`（启动需约 60s 等 Payara 初始化） |
| 注意 | Payara JVM 参数需两次重启才生效（asadmin 行为，第一次写 domain.xml，第二次生效） |

---

## 服务启动依赖关系（当前）

```
zookeeper
    └── kafka (healthy)
            ├── conversion
            └── back-py
                    ├── db (healthy)
                    └── kafka (started)

es (healthy)
    └── back-py（直接查询，无 depends_on，启动后 ES fallback 到 DB）
    └── [kibana — 按需手动启]

front ◄── ssl-proxy
adminer ◄── db

[back — 按需手动启，不在自动依赖链中]
```

---

## 数据卷说明

| 卷名 | 类型 | 当前大小 | 说明 |
|------|------|---------|------|
| `db-volume` | Docker named volume | 72 MiB | PostgreSQL 数据文件 |
| `es-volume` | Docker named volume | 10 MiB | Elasticsearch 索引 |
| `conversion-volume` | Docker named volume | ~0（已清空） | CAD 转换临时目录（可定期清空） |
| `./data/vault` | bind mount | 7.9 MiB | CAD 原文件 + 生成的 GLB（宿主路径 `docdoku-plm-docker/data/vault/`） |

---

## 资源用量（参考，2026-07-10 采样）

| 容器 | 内存 | 备注 |
|------|------|------|
| back-py | 175 MiB | 主后端 |
| es | 1.24 GiB | 全文搜索 |
| kafka | 408 MiB | 消息队列 |
| kibana | — | 已停，按需启 |
| zookeeper | 160 MiB | Kafka 协调 |
| conversion | 138 MiB | CAD 转换 |
| db | 45 MiB | 数据库 |
| front | 14 MiB | 静态文件 + 代理 |
| ssl-proxy | 12 MiB | HTTPS |
| adminer | 10 MiB | DB 管理 |
| smtp | 3 MiB | 邮件调试 |
| **back（已停）** | **0**（原 3.29 GiB） | 停用后释放 |

---

## 端口速查表

| 端口 | 服务 | 说明 |
|------|------|------|
| **8000** | front | PLM Web 前端（主 HTTP 入口） |
| **9000** | ssl-proxy | HTTPS 反向代理（公网入口 cwbcode.ddnsto.com） |
| **8009** | back-py | FastAPI 后端（直连调试） |
| **5432** | db | PostgreSQL 直连 |
| **8003** | smtp | MailHog Web UI（邮件查看） |
| **8004** | adminer | PostgreSQL Web 管理 |
| 8002 | kibana | ES 可视化（按需手动启） |
| 8001 | back | Payara REST（已停用，按需手动启） |
| 8005 | front:85 | Payara 对比端口（已停用） |
| 11025 | smtp | SMTP 协议端口 |

---

## 关键数据流

### CAD 文件上传与三维预览生成

```
用户上传 .stp 文件
    │
    ▼
back-py (FastAPI REST API)
    ├── 保存 .stp 到 vault（./data/vault/{ws}/parts/{pn}/{ver}/{iter}/nativecad/）
    ├── 在 DB 创建 Conversion 记录（pending=true, succeed=false）
    └── 发布 ConversionOrder 到 Kafka topic CONVERT
            │
            ▼
    conversion 服务消费 Kafka 消息
        ├── 读取 vault 中的 .stp 文件
        ├── 生成 .glb 文件（写入 conversion-volume 临时目录）
        ├── Decimation 减面（一直失败，已知问题，不阻止 GLB 生成）
        └── PUT http://back-py:8000/.../conversion 回调
                │
                ▼
        back-py handleConversionResultCallback
            ├── 查 DB 找 pending=true 的 Conversion 记录（按 partRevision 定位，避免 race）
            ├── 将 .glb 写入 vault
            ├── 在 DB 写入 Geometry 记录
            └── 更新 Conversion（pending=false, succeed=true）
                        │
                        ▼
            前端轮询 / WebSocket 通知，显示 3D 预览
```

### 自定义查询执行（Query Builder）

```
前端 POST /workspaces/{ws}/parts/queries?export=JSON
    body: { queryRule: {AND/OR 嵌套树}, selects: [...], contexts: [...] }
        │
        ▼
back-py query_executor.py
    ├── build_part_where()：递归编译 QueryRule → 参数化 SQL WHERE 片段
    │   支持 11 种 field 前缀（pm./pr./author./attr-TYPE./pd-attr-TYPE.）
    ├── run_part_query()：执行 SQL，后过滤（已检入迭代 + ACL 权限）
    └── [如有 contexts] query_pbs.py
        ├── PSFilterVisitor 遍历装配结构 → QueryResultRow（含 depth/amount/P2P）
        └── merge_rows()：PBS 结果 ∩ 查询结果 → 最终交集
```

### Excel 属性批量导入

```
前端 POST /workspaces/{ws}/parts/importPreview (dry-run)
前端 POST /workspaces/{ws}/parts/import (执行)
    body: multipart/form-data  upload=<.xlsx>
        │
        ▼
back-py
    ├── excel_parser.parse_excel()：解析 .xlsx（表头正则/cell comment/多值拆分/类型校验）
    ├── [dry-run] attributes_importer_utils.would_change()：预判是否需要 checkout
    └── [执行] ImporterService.import_into_parts()
        ├── 查 PartMaster → 校验写权限/checkout 状态
        ├── 加载现有 instanceAttributes → merge_attributes()（update/create/DuplicateEntry 等）
        ├── 错误门控：有错 → 返回失败，不写 DB
        └── 写入循环：checkout → _write_iteration_attributes（写 dtype）→ commit → checkin
```
