# 关于 localhost:8080 中文切换及中文支持

## 在哪里切换语言？

系统语言在**账户设置**中切换：

1. 登录后，点击右上角的用户头像或用户名
2. 进入 **Account（账户）** 或 **Edit account（编辑账户）**
3. 找到 **Language（语言）** 下拉菜单，选择目标语言
4. 保存后**刷新页面**即可生效（系统会提示需要刷新）

注册时也可在注册表单的 **Language** 字段直接选择语言。

---

## 原有中文支持情况

在修改之前，系统**不支持中文**。支持的语言只有：

| 语言代码 | 语言名称 |
|---------|---------|
| en | English（默认） |
| fr | Français |
| es | Español |
| ru | Русский |

---

## 已完成的中文支持修改

本次修改为系统全面添加了**简体中文（zh）**支持，具体改动如下：

### 前端翻译文件（10 个新文件）
在 `docdoku-plm-front/app/js/localization/nls/zh/` 目录下创建了所有翻译文件：
- `index.js` — 登录/首页文字
- `common.js` — 700+ 条通用界面文字（全部翻译）
- `account-management.js` — 账户管理页面
- `change-management.js` — 变更管理页面
- `document-management.js` — 文档管理页面
- `download.js` — 下载页面
- `organization-management.js` — 组织管理页面
- `product-management.js` — 产品管理页面
- `product-structure.js` — 产品结构页面
- `workspace-management.js` — 工作区管理页面

### 前端语言注册（10 个文件更新）
在所有 root NLS bundle 文件中添加了 `'zh': true`，并在语言列表中添加了 `zh: '中文'`。

### 后端支持（7 个文件）
- `PropertiesLoader.java` — 添加 `"zh"` 到支持语言数组，添加 `case "zh"` 分支
- `LocalStrings_zh.properties`（server-core）— 约 160 条异常消息翻译
- `LocalStrings_zh.properties`（server-rest）— 查询字段标签翻译
- `NotificationText_zh.properties` — 邮件通知模板翻译
- `Importers_zh.properties` — 导入错误消息翻译
- `TitleBlockData_zh.properties` — 文档标题块字段翻译
- `ExcelImport_zh.properties` — Excel 导入验证消息翻译

---

# 关于 `env/back.env` 中账号密码的说明

## 原因解释

`back.env` 中的各项 `changeit` 是**系统内部组件之间通信的密码**，不是 PLM 用户账号：

| 变量 | 含义 | 用途 |
|------|------|------|
| `DATABASE_USER` / `DATABASE_PWD` | 数据库连接账号 | 后端服务访问 PostgreSQL 数据库用，不是登录账号 |
| `JWT_KEY` | JSON Web Token 签名密钥 | 用于加密用户 token，不是账号密码 |
| `KEYSTORE_PASS` | Java 密钥库密码 | 用于加解密内部通信，不是账号密码 |

---

## 正确的登录方式

`http://localhost:8000` 的 PLM 用户账号**需要你自己注册创建**，系统不预置任何默认账号。

**首次使用步骤：**

1. 打开浏览器访问 **http://localhost:8000**
2. 点击页面上的 **Sign up**（注册）
3. 填写用户名、邮箱和密码，完成注册
4. 用刚注册的账号登录即可

> **关于 `#recovery` 页面**：这是密码找回/重置页面，不是普通登录入口。正常登录应该在首页直接输入账号密码，或点击 **Login** 按钮。

---

# 语言下拉菜单中没有中文选项的根本原因及解决方案

## 根本原因

语言下拉菜单的选项由**后端 Java API**（`GET /api/languages` → `PropertiesLoader.SUPPORTED_LANGUAGES[]`，编译进后端 JAR）控制，**不是**前端 NLS 翻译文件控制的。

前端 Mustache 模板只负责为已存在的选项添加标签，无法注入新的选项。因此，只挂载前端翻译文件（方案 A）对下拉菜单没有任何效果。

---

## 解决方案 X（最简单 — nginx 拦截 `/languages` 接口，无需重建镜像）

### 第 1 步：新建 `docdoku-plm-docker/proxy/languages.json`

```json
["fr", "en", "ru", "zh"]
```

### 第 2 步：修改 `docdoku-plm-docker/proxy/nginx.conf`

在 `/api` location 之前添加精确匹配规则，拦截 `/languages` 请求并返回静态 JSON：

```nginx
location = /docdoku-plm-server-rest/api/languages {
    default_type application/json;
    alias /etc/nginx/conf.d/languages.json;
}
```

### 第 3 步：修改 `docker-compose.yml`（`ssl-proxy` 服务），挂载该文件

```yaml
volumes:
  - ./proxy/ssl:/etc/nginx/ssl
  - ./proxy/nginx.conf:/etc/nginx/conf.d/default.conf
  - ./proxy/languages.json:/etc/nginx/conf.d/languages.json   # 新增
```

### 第 4 步：重启 nginx 容器

```bash
docker compose up --force-recreate --no-deps -d ssl-proxy
```

> ⚠️ **前提**：必须通过 `https://docdokuplm.local:9000`（即走 nginx ssl-proxy）访问，而非直接访问 `http://localhost:8000` 的 front 容器。如果直接访问 front 容器，nginx 不在请求路径上，此方案无效，需使用下面的方案 B。

---

## 解决方案 B（最彻底 — 重建后端镜像）

本仓库的 `PropertiesLoader.java` 已经包含 `"zh"`，直接重新构建即可：

```bash
# 在仓库根目录
cd docdoku-plm-server
mvn clean package -DskipTests

# 重建 Docker 镜像
docker build -t docdoku-plm-server:zh-local .

# 修改 docker-compose.yml 中 back 服务的 image 指向新镜像
# image: docdoku-plm-server:zh-local

docker compose up --force-recreate --no-deps -d back
```
