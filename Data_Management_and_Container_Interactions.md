# 项目数据管理分析：Volumes 与容器交互（2026-05-15 新增）

## 一、总体架构

本项目通过 `docdoku-plm-docker/docker-compose.yml` 定义了 **11 个容器**，统一接入一个名为 `network` 的 bridge 网络，容器间通过服务名（DNS 解析）相互访问。

---

## 二、Named Volumes（命名卷）

共定义 **4 个命名卷**，由 Docker 引擎管理，数据持久化于宿主机 Docker volume 存储区：

| Volume 名称 | 挂载到哪些容器 | 容器内路径 | 用途 |
|---|---|---|---|
| `db-volume` | `db` | `/var/lib/postgresql/data` | PostgreSQL 数据库数据持久化 |
| `es-volume` | `es` | `/usr/share/elasticsearch/data` | Elasticsearch 索引数据持久化 |
| `docdoku-plm-server-volume` | `back` | `/var/lib/docdoku/vault` | 用户上传文件的主存储区（文件库/vault） |
| `docdoku-plm-server-volume` | `conversion` | `/data/vault` | 转换服务读取原始文件（同一卷，不同挂载点） |
| `conversion-volume` | `back` | `/var/lib/docdoku/conversions` | 文件转换任务及结果的存储区 |
| `conversion-volume` | `conversion` | `/data/conversions` | 转换服务写入转换结果（同一卷，不同挂载点） |

### 关键设计：两个共享卷

- **`docdoku-plm-server-volume`（文件库）**：`back` 容器写入用户上传的原始文件，`conversion` 容器通过同一卷读取这些文件进行格式转换。两者挂载路径不同，但底层是同一块存储。
- **`conversion-volume`（转换区）**：`conversion` 容器将转换结果写入，`back` 容器读取已转换的文件。同样是两容器共享一卷。

---

## 三、Bind Mounts（绑定挂载）

这些是将宿主机（或代码仓库）中的具体文件/目录直接挂载到容器中，主要用于配置注入：

| 宿主机路径 | 目标容器 | 容器内路径 | 用途 |
|---|---|---|---|
| `./env/front.json` | `front` | `/usr/share/nginx/html/webapp.properties.json` | 前端运行时配置（后端地址等） |
| `../docdoku-plm-front/app/js/localization/nls` | `front` | `/usr/share/nginx/html/js/localization/nls` | 中文本地化翻译文件 |
| `./front/nginx.conf` | `front` | `/etc/nginx/conf.d/default.conf` | 前端 nginx 配置（支持 UTF-8 中文） |
| `./keystore` | `back` | `/opt/payara41/keystore` | SSL/TLS 密钥库 |
| `./proxy/ssl` | `ssl-proxy` | `/etc/nginx/ssl` | SSL 证书文件 |
| `./proxy/nginx.conf` | `ssl-proxy` | `/etc/nginx/conf.d/default.conf` | 反向代理 nginx 配置 |

---

## 四、容器交互关系

### 4.1 网络通信依赖图

```
用户浏览器
    │
    ▼ :9000 (HTTPS)
┌─────────────┐
│  ssl-proxy  │  (nginx 反向代理)
└─────────────┘
    │               │
    ▼ :80           ▼ :8080
┌────────┐     ┌──────┐
│ front  │     │ back │ ◄── back.env 配置
└────────┘     └──────┘
                   │        │        │
                   ▼        ▼        ▼
                ┌────┐  ┌────┐  ┌──────┐
                │ db │  │ es │  │ smtp │
                └────┘  └────┘  └──────┘
                           │
                           ▼
                       ┌───────┐
                       │kibana │ :8002
                       └───────┘
┌────────────┐   Kafka消息   ┌──────────┐   ┌───────────┐
│ conversion │ ◄──────────── │  kafka   │ ◄─│ zookeeper │
└────────────┘               └──────────┘   └───────────┘
      │  回调 REST API
      ▼
   back:8080
┌─────────┐
│ adminer │ :8004  ──► db
└─────────┘
```

### 4.2 各容器详细交互说明

#### `front`（前端 UI，nginx）
- **对外**：暴露 `:8000`（HTTP），通过 ssl-proxy 转发
- **访问 back**：浏览器直接向 `localhost:8001` 发 REST/WebSocket 请求（由 `front.json` 配置）

#### `back`（Java EE 应用服务器，Payara）
- **访问 `db`**：通过 `DATABASE_SERVER_NAME=db`（PostgreSQL，默认端口 5432）存储业务数据（用户、项目、元数据等）
- **访问 `es`**：通过 `ES_SERVER_URI=http://es:9200` 进行全文索引与搜索
- **访问 `smtp`**：通过 `SMTP_HOST=smtp:1025` 发送邮件通知
- **与 `conversion`**：通过共享 Volume（`docdoku-plm-server-volume` + `conversion-volume`）传递文件，通过 Kafka 发送转换任务

#### `conversion`（文件格式转换服务）
- **访问 `kafka`**：订阅 `kafka:9092` 上的转换任务消息
- **访问 `back`**：通过 `ENDPOINT=http://back:8080/docdoku-plm-server-rest/api` 回调，通知转换完成
- **依赖 `back`** 启动后才启动（`depends_on: - kafka - back`）

#### `es`（Elasticsearch）
- 被 `back` 用于全文搜索索引
- 被 `kibana` 用于可视化管理

#### `db`（PostgreSQL）
- 被 `back` 存储所有关系型业务数据
- 被 `adminer` 提供 Web UI 管理界面

#### `kafka` + `zookeeper`（消息队列）
- `kafka` 依赖 `zookeeper` 进行集群协调
- `back` 发布文件转换任务消息到 Kafka
- `conversion` 消费 Kafka 消息并执行转换

#### `ssl-proxy`（HTTPS 入口，nginx）
- 对外统一暴露 `:9000`（HTTPS）
- `/` → 代理到 `front:80`
- `/docdoku-plm-server-rest/api` → 代理到 `back:8080`
- `/docdoku-plm-server-rest/ws` → WebSocket 代理到 `back:8080`

---

## 五、文件转换完整数据流

```
1. 用户通过浏览器上传文件
        ↓
2. back 将文件写入 docdoku-plm-server-volume（/var/lib/docdoku/vault）
        ↓
3. back 向 Kafka 发布转换任务消息（包含文件路径信息）
        ↓
4. conversion 从 Kafka 消费消息
        ↓
5. conversion 从共享 docdoku-plm-server-volume（/data/vault）读取原始文件
        ↓
6. conversion 执行格式转换（如 CAD → 预览图）
        ↓
7. conversion 将结果写入 conversion-volume（/data/conversions）
        ↓
8. conversion 调用 back REST API 回调，通知转换完成
        ↓
9. back 从 conversion-volume（/var/lib/docdoku/conversions）读取转换结果
```

---

## 六、对外暴露端口汇总

| 端口 | 容器 | 说明 |
|---|---|---|
| 8000 | `front` | 前端 UI（HTTP） |
| 8001 | `back` | REST API + WebSocket |
| 8002 | `kibana` | Elasticsearch 可视化 |
| 8003 | `smtp` | MailHog Web UI（邮件测试） |
| 8004 | `adminer` | 数据库 Web 管理 |
| 9000 | `ssl-proxy` | HTTPS 统一入口 |
| 1025 | `smtp` | SMTP 协议端口 |

---

## 七、总结

| 层次 | 技术 | 说明 |
|---|---|---|
| 持久化存储 | Named Volumes | db-volume、es-volume 分别持久化数据库和搜索引擎数据 |
| 跨容器文件共享 | Named Volumes（共享） | vault 卷 + conversions 卷在 back 和 conversion 间共享文件 |
| 配置注入 | Bind Mounts | 将 env 文件、nginx.conf、keystore 挂载进容器 |
| 容器通信 | Bridge 网络 + 服务名DNS | 所有容器在同一 network，通过服务名寻址 |
| 异步任务 | Kafka 消息队列 | back → kafka → conversion 解耦文件转换流程 |

---

# 去除西班牙语（es）支持的完整 Plan

---

## 涉及文件总览

西班牙语在本项目中分为两层：

| 层次 | 位置 | 说明 |
|---|---|---|
| **前端 NLS bundle 声明** | `docdoku-plm-front/app/js/localization/nls/*.js`（7个文件） | 每个文件中有 `'es': true`，告知 RequireJS 存在 es 子目录 |
| **前端 NLS 翻译文件** | `docdoku-plm-front/app/js/localization/nls/es/common.js`（1个文件） | 唯一的西班牙语翻译文件 |
| **后端语言列表** | `docdoku-plm-server/docdoku-plm-server-i18n/src/main/java/com/docdoku/plm/server/i18n/PropertiesLoader.java` | `SUPPORTED_LANGUAGES` 数组中**已不含 "es"**（已是 `{"fr", "en", "ru", "zh"}`）|
| **后端属性资源文件** | `docdoku-plm-server/**/*_es.properties` | **不存在**，后端从未有西班牙语资源 |

## 执行步骤

### Step 1：删除唯一的西班牙语翻译文件目录

```
docdoku-plm-front/app/js/localization/nls/es/
└── common.js   ← 删除整个 es/ 目录
```

### Step 2：在 7 个 NLS bundle 根文件中移除 `'es': true` 声明

以下每个文件都有 `'es': true`（或 `es: true`），需要删除这一行：

1. `docdoku-plm-front/app/js/localization/nls/common.js`
2. `docdoku-plm-front/app/js/localization/nls/index.js`
3. `docdoku-plm-front/app/js/localization/nls/account-management.js`
4. `docdoku-plm-front/app/js/localization/nls/workspace-management.js`
5. `docdoku-plm-front/app/js/localization/nls/download.js`
6. `docdoku-plm-front/app/js/localization/nls/product-management.js`
7. `docdoku-plm-front/app/js/localization/nls/document-management.js`
8. `docdoku-plm-front/app/js/localization/nls/change-management.js`
9. `docdoku-plm-front/app/js/localization/nls/product-structure.js`
10. `docdoku-plm-front/app/js/localization/nls/organization-management.js`

（注：index.js 当前内容为 `define({});`，需确认是否有 es 条目）

### Step 3：确认后端无需修改

`PropertiesLoader.java` 的 `SUPPORTED_LANGUAGES` 数组已经是 `{"fr", "en", "ru", "zh"}`，不含 "es"，**后端无需改动**。

### Step 4：验证

- 在账号设置的语言下拉列表中，确认"西班牙语"选项不再出现（该列表由后端 `/api/languages` 接口驱动）
- 由于后端已不返回 "es"，语言下拉里本来就没有西班牙语选项，删除前端 NLS 文件后，即使有人手动切换到 es 语言 cookie，RequireJS 也不会尝试加载 es 翻译，会 fallback 到英语

## 改动规模估计

| 类型 | 数量 |
|---|---|
| 删除目录/文件 | 1 个目录（`nls/es/`），含 1 个文件 |
| 修改文件（各删 1 行） | 最多 10 个 NLS bundle JS 文件 |
| 后端修改 | 0 |


---

# localhost:8004 操作说明 & 全系统账号密码总览（2026-05-15 新增）

---

## 一、localhost:8004 是什么？能做什么？

根据 `docdoku-plm-docker/docker-compose.yml`：

```yaml
adminer:
  image: adminer:4.7.1-standalone
  ports:
    - 8004:8080
  depends_on:
    - db
```

**:8004 是 [Adminer](https://www.adminer.org/) 数据库管理工具的 Web 界面**，连接到本系统的 PostgreSQL 数据库容器（`db`）。

### 可以进行的操作

| 操作类型 | 具体内容 |
|---|---|
| **查看数据** | 浏览所有数据库表、查看行记录 |
| **执行 SQL** | 运行任意 SELECT/INSERT/UPDATE/DELETE/DDL 语句 |
| **修改数据** | 直接编辑表中的字段值（包括用户账号、密码哈希） |
| **导出/导入** | 导出 SQL 或 CSV，导入 SQL 脚本 |
| **表结构管理** | 查看表结构、索引、外键关系 |
| **用户账号管理** | 直接操作 `ACCOUNT`、`USERGROUPMAPPING` 等核心表 |

> ⚠️ **Adminer 可以绕过应用层权限，直接修改数据库**，因此**生产环境必须关闭或限制访问**（README 中也有此警告）。

### 登录方式

在 Adminer 登录页面填写：
- **系统**：PostgreSQL
- **服务器**：`db`（Docker 内部网络名）
- **用户名**：`changeit`（见 `env/db.env`）
- **密码**：`changeit`
- **数据库**：`docdokuplm`

---

## 二、全系统账号密码总览

本系统共有以下几类凭据，全部集中在 `docdoku-plm-docker/env/` 目录的配置文件中：

### 1. PostgreSQL 数据库账号（`env/db.env`）

| 项目 | 值 |
|---|---|
| 数据库名 | `docdokuplm` |
| 用户名 | `changeit` |
| 密码 | `changeit` |
| 用途 | Adminer 登录、后端服务连接数据库 |

### 2. 后端应用配置凭据（`env/back.env`）

| 项目 | 值 | 用途 |
|---|---|---|
| `DATABASE_USER` | `changeit` | 后端连接 PostgreSQL |
| `DATABASE_PWD` | `changeit` | 后端连接 PostgreSQL |
| `JWT_KEY` | `changeit` | JWT Token 签名密钥 |
| `KEYSTORE_PASS` | `changeit` | PKCS12 密钥库密码 |
| `KEYSTORE_KEY_PASS` | `changeit` | 密钥库中密钥的密码 |
| `SMTP_USER` | `DocDokuPLM` | SMTP 发件用户名（MailHog 无需真实密码）|
| `ES_PREFIX` | `changeit` | Elasticsearch 索引前缀（非真正密码）|
| `ES_SERVER_USERNAME` | （空） | Elasticsearch 无认证 |
| `ES_SERVER_PWD` | （空） | Elasticsearch 无认证 |

### 3. 密钥库生成参数（`start.sh`）

| 项目 | 值 |
|---|---|
| `STOREPASS` | `changeit` |
| `KEYPASS` | `changeit` |
| `KEYALIAS` | `mykeyalias` |

### 4. DocDokuPLM 应用层账号（用户自己创建，存储在 PostgreSQL）

应用层账号**没有预置默认账号**，需要在首次访问 `localhost:8000`（或 `:9000`）时**通过注册界面创建**。规则如下：

| 角色 | 创建方式 | 说明 |
|---|---|---|
| **普通用户** | 在前端登录页点击 Register 注册 | 密码以摘要算法（SHA等）存储在 `ACCOUNT` 表 |
| **超级管理员（admin）** | 第一个注册的账号自动成为 admin，或通过 Adminer 直接修改 `USERGROUPMAPPING` 表 | `groupName = 'admin'` |
| **普通用户（users）** | 注册后默认分配 | `groupName = 'users'` |

---

## 三、怎样修改账号和密码？

### 方法一：通过前端应用修改（推荐，普通场景）

1. 登录 `localhost:8000`（或 `:9000`）
2. 右上角 → **账号设置**（Account Edition）
3. 修改姓名、邮箱、语言、时区，**填写新密码后保存**
4. 如果忘记密码，在登录页点击 **"Forgot your password?"**，系统会发送邮件到 MailHog（`localhost:8003` 可查看）

### 方法二：通过 Adminer（:8004）直接修改数据库（管理员/应急场景）

1. 打开 `http://localhost:8004`，用 PostgreSQL + db / changeit / changeit / docdokuplm 登录
2. 找到 `ACCOUNT` 表，查看字段 `login`、`password`（哈希值）
3. 用 SQL 直接更新密码哈希（需要先计算新密码的 SHA-256 摘要，与后端 `digestAlgorithm` 一致）：
   ```sql
   UPDATE ACCOUNT SET password = '<新密码的SHA-256哈希> ' WHERE login = '<用户名>';
   ```
4. 若要将某账号升级为 admin，修改 `USERGROUPMAPPING` 表：
   ```sql
   UPDATE USERGROUPMAPPING SET groupname = 'admin' WHERE login = '<用户名>';
   ```

### 方法三：修改各服务凭据（如 DB 密码、JWT Key 等）

1. 编辑 `docdoku-plm-docker/env/db.env`、`back.env`、`start.sh` 中的 `changeit`
2. 重启相关容器：
   ```bash
   docker-compose up --force-recreate --no-deps db back
   ```

---

## 四、安全提醒

所有凭据当前均为默认值 `changeit`，**生产部署前必须全部修改**，参考 README：
> "Make sure to edit all passwords in env files before you start the script."
