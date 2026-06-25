# 容器架构说明

本项目基于 DocDoku PLM 2.6.2 二次开发，通过 Docker Compose 编排运行。所有容器处于同一个自定义 bridge 网络（`docdoku-plm-docker_network`），容器间通过服务名互相访问。

---

## 整体架构图

```
用户浏览器 / CATIA Copilot 工具
        │
        ▼
┌───────────────────────────────────────────────────────────────────┐
│  宿主机端口                                                       │
│                                                                   │
│  :8000 (HTTP)  ──── front  (Nginx 前端静态文件)                   │
│  :9000 (HTTPS) ──── ssl-proxy (Nginx SSL 反向代理)                │
│  :8001 (HTTP)  ──── back   (Payara 后端应用服务器)                │
│  :5432         ──── db     (PostgreSQL 数据库)                    │
│  :8002         ──── kibana (ES 可视化，运维用)                    │
│  :8003         ──── smtp   (MailHog 邮件调试)                     │
│  :8004         ──── adminer(数据库 Web 管理)                      │
│  :11025        ──── smtp   (SMTP 协议端口)                        │
└───────────────────────────────────────────────────────────────────┘
        │
        ▼ Docker 内部网络（容器名互访）
┌───────────────────────────────────────────────────────────────────┐
│                                                                   │
│  front ◄──────────────────────────────────── back:8080            │
│                                                  │                │
│                         ┌────────────────────────┤                │
│                         ▼                        ▼                │
│                        db:5432              es:9200               │
│                         │                        │                │
│                         │                   kibana:5601           │
│                         ▼                                         │
│                     adminer:8080                                  │
│                                                                   │
│  back ──── Kafka Producer ──► kafka:9092 ◄── zookeeper:2181       │
│                                    │                              │
│                                    ▼                              │
│                              conversion:8080                      │
│                                    │                              │
│                                    ▼ HTTP PUT 回调                │
│                               back:8080/api/...                   │
│                                                                   │
│  back ◄──► smtp:1025  (发送系统邮件)                              │
└───────────────────────────────────────────────────────────────────┘
```

---

## 容器详细说明

### 1. front — 前端 Web 界面

| 项目 | 内容 |
|------|------|
| 镜像 | `docdoku/docdoku-plm-front:2.6.2`（本地构建） |
| 宿主机端口 | `8000:80` |
| 职责 | 提供 PLM 系统的 Web 前端（Backbone.js SPA），包含零件管理、文档管理、产品结构树、3D 预览等所有界面 |
| 技术栈 | Nginx 托管静态文件，RequireJS 模块化，WebGL 三维预览 |
| 配置文件 | `env/front.json` 挂载到 `/usr/share/nginx/html/webapp.properties.json`，告知前端 API 地址、端口、WebSocket 地址 |
| Nginx 配置 | `front/nginx.conf` 挂载，添加了 `charset=utf-8` 支持中文 NLS |
| 本地修改 | 增加中文界面支持、账号表单校验、CAD 文件格式白名单、上传编码修复 |
| 构建方式 | `cd docdoku-plm-front && nvm use 14 && npm run build && docker build -f docker/Dockerfile -t docdoku/docdoku-plm-front:2.6.2 .` |

---

### 2. back — 后端应用服务器（核心服务）

| 项目 | 内容 |
|------|------|
| 镜像 | `docdoku/docdoku-plm-server:2.6.2`（本地构建） |
| 宿主机端口 | `8001:8080`（HTTP REST API） |
| 应用服务器 | Payara 5.194（GlassFish 衍生版，Java EE 8） |
| 职责 | 系统核心：处理所有业务逻辑，提供 RESTful API，管理零件/文档/工作区/工作流，触发 CAD 文件转换，处理转换回调，发送邮件通知 |
| JVM 配置 | `-Xmx4g -Xms4g`（通过 `HEAP_SIZE=4g` 环境变量控制），G1GC，MetaspaceSize=256m，MaxMetaspaceSize=2g |
| API 路径 | `http://localhost:8001/docdoku-plm-server-rest/api/` |
| 依赖容器 | `db`（PostgreSQL）、`es`（Elasticsearch）、`smtp`（邮件）、`kafka`（CAD 转换消息队列） |
| 数据卷 | `./data/vault` → `/var/lib/docdoku/vault`（CAD 原文件和生成的 GLB 文件）<br>`conversion-volume` → `/var/lib/docdoku/conversions`（转换临时目录） |
| 认证机制 | JWT（默认启用）+ Basic Auth（已禁用），密码以 MD5 hash 存储于 `credential` 表 |
| 本地修改 | 修复 `ConverterBean.handleConversionResultCallback` 的 `lastIteration()` race condition（改为查 pending conversion 记录）；空几何体（no geometry generated）标记为 succeed=true；中文支持；多处 NPE 修复 |
| 构建方式 | `cd docdoku-plm-server && mvn clean install -DskipTests && docker build --build-arg VERSION=2.6.2 -f docker/Dockerfile -t docdoku/docdoku-plm-server:2.6.2 .` |

**重要**：`back` 容器每次重启需要两次才能让 JVM 参数（如 `-Xmx4g`）生效。第一次重启会把参数写入 Payara 的 `domain.xml`，第二次重启才真正以新参数启动 JVM。这是 Payara asadmin 的已知行为，由 `docker/asadmin.commands` 文件控制启动时命令。

---

### 3. conversion — CAD 文件转换服务

| 项目 | 内容 |
|------|------|
| 镜像 | `docdoku/docdoku-plm-conversion-service:2.6.2`（有源码，位于 `docdoku-plm-conversion-service/`） |
| 职责 | 监听 Kafka 消息队列（topic: `CONVERT`），将 STEP/STL/OBJ/DAE/IFC 等 CAD 文件转换为 GLB 格式供浏览器三维预览，转换完成后回调 back 端 REST API |
| 转换流程 | Kafka 消费消息 → 读取 vault 中的 `.stp` 文件 → 调用内置转换工具生成 `.glb` → 尝试 Decimation（减面优化，当前一直失败）→ `PUT /api/.../conversion` 回调 back |
| 回调接口 | `PUT /docdoku-plm-server-rest/api/workspaces/{ws}/parts/{pn}/versions/{ver}/conversion` |
| 数据卷 | `./data/vault` → `/data/vault`（与 back 共享，读取原始 CAD 文件、写入生成的 GLB）<br>`conversion-volume` → `/data/conversions`（转换临时目录，与 back 共享） |
| 已知问题 | Decimation（减面优化）一直报 `Decimation failed with code = 1 read error`，这是已知问题，不影响 GLB 文件生成 |
| 空几何体处理 | 若 STEP 文件不含实体（如运动学约束件、坐标系定义件），转换器报 `no geometry generated`，back 端已修复为标记 `succeed=true` 而非 `succeed=false` |
| Kafka 配置 | `acks=0`（fire-and-forget，不等待确认），`retries=1`，`linger.ms=33` |

---

### 4. db — 关系型数据库

| 项目 | 内容 |
|------|------|
| 镜像 | `postgres:13.1-alpine` |
| 宿主机端口 | `5432:5432` |
| 数据库名 | `docdokuplm` |
| 账号 | `changeit` / `changeit`（用户名/密码） |
| 职责 | 存储系统所有业务数据：用户账号、工作区、零件主记录（PartMaster）、零件版本（PartRevision）、零件迭代（PartIteration）、装配关系（PartUsageLink）、转换状态（Conversion）、文档、工作流等 |
| 数据卷 | `db-volume`（Docker named volume，由 Docker 管理，PostgreSQL 对文件权限敏感） |
| 健康检查 | `pg_isready -U docdokuplm`，间隔 5s，back 等待其 healthy 后才启动 |
| 主要业务表 | `account`（用户）、`credential`（密码 hash）、`workspace`（工作区）、`partmaster`（零件主）、`partrevision`（版本）、`partiteration`（迭代）、`conversion`（转换状态）、`partusagelink`（装配关系） |

---

### 5. es — 全文搜索引擎

| 项目 | 内容 |
|------|------|
| 镜像 | `docker.elastic.co/elasticsearch/elasticsearch:6.6.1` |
| 内部端口 | `9200`（HTTP），`9300`（节点间通信） |
| 职责 | 为零件、文档提供全文检索能力，back 端在创建/更新零件迭代时自动同步索引（`IndexerManagerBean`）；前端的搜索功能依赖此服务 |
| 配置 | 单节点模式（`discovery.type=single-node`），JVM 堆 512m，内存锁定（`bootstrap.memory_lock=true`） |
| 数据卷 | `es-volume`（Docker named volume） |
| 健康检查 | 查询 `/_cluster/health`，排除 `status:red`，启动等待期 60s |

---

### 6. kibana — Elasticsearch 可视化

| 项目 | 内容 |
|------|------|
| 镜像 | `docker.elastic.co/kibana/kibana:6.6.1` |
| 宿主机端口 | `8002:5601` |
| 职责 | Elasticsearch 的 Web 可视化管理界面，用于运维场景：查看 ES 索引状态、执行搜索调试、监控索引健康 |
| 使用场景 | 仅运维/开发调试使用，正常业务流程中不涉及 |

---

### 7. zookeeper — 分布式协调服务

| 项目 | 内容 |
|------|------|
| 镜像 | `confluentinc/cp-zookeeper:7.6.1` |
| 内部端口 | `2181` |
| 职责 | Kafka 的元数据管理和 broker 协调服务。Kafka 依赖 ZooKeeper 维护 broker 注册信息、topic 配置、consumer group offset 等 |
| 对外暴露 | 不对宿主机暴露端口，仅供 Kafka 内部使用 |

---

### 8. kafka — 消息队列

| 项目 | 内容 |
|------|------|
| 镜像 | `confluentinc/cp-kafka:7.6.1` |
| 内部地址 | `kafka:9092` |
| 职责 | 异步传递 CAD 文件转换任务。back 端上传 CAD 文件后，将转换指令（`ConversionOrder`，含文件路径、JWT token 等）发布到 topic `CONVERT`；conversion 服务消费该 topic 执行转换 |
| Topic | `CONVERT`（单 partition，replication factor 1） |
| Consumer Group | `conversions_group` |
| 关键配置 | `KAFKA_AUTO_CREATE_TOPICS_ENABLE=true`（topic 自动创建），`KAFKA_LOG_RETENTION_HOURS=1`（日志仅保留 1 小时） |
| 健康检查 | `kafka-broker-api-versions` 检查 broker 可用性，back 容器不等待 kafka healthy（startup race condition 已知问题，kafka 短暂不可用时 `acks=0` 可能静默丢消息） |

---

### 9. smtp — 邮件服务（调试用）

| 项目 | 内容 |
|------|------|
| 镜像 | `mailhog/mailhog:v1.0.1` |
| 宿主机端口 | `11025:1025`（SMTP）、`8003:8025`（Web UI） |
| 职责 | 拦截系统发出的所有邮件（工作流通知、账号激活等），在 Web 界面（`:8003`）中展示，不真正发送到收件人。用于开发/测试环境调试邮件功能 |

---

### 10. adminer — 数据库管理界面

| 项目 | 内容 |
|------|------|
| 镜像 | `adminer:4.8.1` |
| 宿主机端口 | `8004:8080` |
| 职责 | PostgreSQL 的 Web 管理界面，用于运维场景：查看表结构、执行 SQL、导出数据等 |
| 登录信息 | 服务器: `db`，数据库: `docdokuplm`，用户名: `changeit`，密码: `changeit` |
| 使用场景 | 仅运维/开发调试使用 |

---

### 11. ssl-proxy — HTTPS 反向代理

| 项目 | 内容 |
|------|------|
| 镜像 | `nginx:1.19.1-alpine` |
| 宿主机端口 | `9000:443` |
| 职责 | 提供 HTTPS 访问入口，将 `/`（前端）和 `/docdoku-plm-server-rest/api`（API）、`/docdoku-plm-server-rest/ws`（WebSocket）分别代理到 front 和 back 容器 |
| 证书 | 自签名证书，位于 `proxy/ssl/`，domain: `docdokuplm.local` |
| WebSocket 支持 | `/docdoku-plm-server-rest/ws` 路径做了 WebSocket upgrade，`proxy_read_timeout 7200s`（2 小时） |

---

## 数据卷说明

| 卷名 | 类型 | 挂载路径 | 说明 |
|------|------|----------|------|
| `db-volume` | Docker named volume | `db:/var/lib/postgresql/data` | PostgreSQL 数据文件，Docker 管理权限 |
| `es-volume` | Docker named volume | `es:/usr/share/elasticsearch/data` | Elasticsearch 索引数据 |
| `conversion-volume` | Docker named volume | `back:/var/lib/docdoku/conversions`<br>`conversion:/data/conversions` | 转换临时目录，back 和 conversion 共享 |
| `./data/vault` | bind mount | `back:/var/lib/docdoku/vault`<br>`conversion:/data/vault` | CAD 原文件（`.stp`、`.CATPart` 等）及生成的 GLB 文件，宿主机路径 `docdoku-plm-docker/data/vault/`，back 和 conversion 共享读写 |

---

## 服务启动依赖关系

```
zookeeper
    └── kafka (healthy)
            └── conversion
            └── back (depends: db healthy, es healthy, smtp started)
                    ├── db (healthy)
                    ├── es (healthy)
                    └── smtp (started)
                            └── front
                            └── adminer
                            └── kibana (depends: es healthy)
                            └── ssl-proxy (depends: front, back)
```

---

## 端口速查表

| 端口 | 服务 | 用途 |
|------|------|------|
| 8000 | front | PLM Web 前端（主入口） |
| 8001 | back | REST API（`/docdoku-plm-server-rest/api/`） |
| 8002 | kibana | Elasticsearch 可视化管理 |
| 8003 | smtp | MailHog Web UI（邮件调试） |
| 8004 | adminer | PostgreSQL Web 管理 |
| 5432 | db | PostgreSQL 直连（客户端工具用） |
| 9000 | ssl-proxy | HTTPS 反向代理入口 |
| 11025 | smtp | SMTP 协议端口 |

---

## 关键数据流

### CAD 文件上传与三维预览生成

```
用户上传 .stp 文件
    │
    ▼
back (REST API)
    ├── 保存 .stp 到 vault（./data/vault/Workspace_X/parts/{pn}/{ver}/{iter}/nativecad/）
    ├── 在 DB 创建 Conversion 记录（pending=true, succeed=false）
    └── 发送 ConversionOrder 到 Kafka topic CONVERT
            │
            ▼
    conversion 服务消费 Kafka 消息
        ├── 读取 vault 中的 .stp 文件
        ├── 调用转换工具生成 .glb 文件（写入 conversion-volume 临时目录）
        ├── 尝试 Decimation 减面优化（当前一直失败，已知问题）
        └── PUT /api/.../conversion 回调 back
                │
                ▼
        back handleConversionResultCallback
            ├── 查找 DB 中 pending=true 的 Conversion 记录（修复后的正确方式）
            ├── 将 .glb 写入 vault
            ├── 在 DB 写入 Geometry 记录
            └── 更新 Conversion 记录（pending=false, succeed=true）
                        │
                        ▼
            前端轮询/WebSocket 通知，显示 3D 预览
```

### 装配结构同步（CATIA Copilot 工具）

```
CATIA Copilot (Windows Python)
    │
    ▼
读取 CATIA COM 对象（Products 树）
    │
    ▼
sync.py _sync_node()
    ├── 后序遍历：先同步子零件，再同步父装配
    ├── 对每个零件调用 PUT /api/workspaces/{ws}/parts/{pn}/versions/{ver}/iterations/{iter}
    │   body 包含：instanceAttributes、components（含 amount 和 cadInstances 矩阵）
    └── amount = len(child.instances)（子零件在父装配中的实例数）
```
