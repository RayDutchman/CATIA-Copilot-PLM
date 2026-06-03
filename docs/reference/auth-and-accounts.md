# DocDokuPLM 邮件系统与账号管理分析

> 分析日期：2026-05-21  
> 分析范围：邮件发送机制、账号注册激活流程、管理员权限与账号管理入口

---

## 一、邮件系统的作用

### 核心实现

邮件发送的核心类是 `NotifierBean.java`，以 EJB Stateless Bean 方式运行，对外暴露 `INotifierLocal` 接口，其他业务 Bean 通过 `@Inject` 注入调用。

```
docdoku-plm-server/docdoku-plm-server-ejb/src/main/java/
  com/docdoku/plm/server/NotifierBean.java
```

底层发送方法（第 704 行）通过 `javax.mail.Transport.send()` 发送 `MimeMessage`，支持 HTML 内容和多语言。

发送路径分两条：
- `sendMessage(Account, ...)` — 系统级通知，不受工作空间开关限制
- `sendMessage(User, ...)` — 先检查 `WorkspaceBackOptions.isSendEmails()` 开关，同时触发 Webhook

### 触发场景（14 种）

| 方法名 | 触发场景 | 调用位置 |
|--------|----------|----------|
| `sendCredential(Account)` | 注册成功，发送欢迎/凭证邮件 | `AccountManagerBean.createAccount()` |
| `sendPasswordRecovery(Account, uuid)` | 密码找回，发送含 UUID 的找回链接 | `UserManagerBean` |
| `sendApproval(...)` 文档 | 文档工作流审批任务分配 | `DocumentWorkflowManagerBean` |
| `sendApproval(...)` 零部件 | 零部件工作流审批任务分配 | `PartWorkflowManagerBean` |
| `sendApproval(...)` 工作空间 | 工作空间工作流审批任务分配 | `WorkflowManagerBean` |
| `sendStateNotification(...)` | 文档生命周期状态变更 | `DocumentWorkflowManagerBean` |
| `sendIterationNotification(...)` | 文档迭代更新（订阅通知） | `SubscriptionManager` |
| `sendTaggedNotification(...)` | 文档/零部件打标签 | `SubscriptionManager` |
| `sendUntaggedNotification(...)` | 文档/零部件去除标签 | `SubscriptionManager` |
| `sendDocumentRevisionWorkflowRelaunchedNotification(...)` | 文档工作流重启 | `DocumentWorkflowManagerBean` |
| `sendPartRevisionWorkflowRelaunchedNotification(...)` | 零部件工作流重启 | `PartWorkflowManagerBean` |
| `sendWorkspaceDeletionNotification(...)` | 工作空间被删除，通知成员 | `WorkspaceManagerBean` |
| `sendWorkspaceIndexationFailure/Success(...)` | 搜索索引任务结果通知 | `IndexerManagerBean` |
| `sendBulkIndexationSuccess/Failure(...)` | 批量索引任务结果通知 | `IndexerManagerBean` |

### 邮件模板位置

模板为多语言 `.properties` 文件，使用 `MessageFormat` 内嵌 HTML 内容：

```
docdoku-plm-server/docdoku-plm-server-ejb/src/main/resources/
  com/docdoku/plm/server/templates/
    NotificationText_en.properties
    NotificationText_zh.properties
    NotificationText_fr.properties
    NotificationText_ru.properties
```

模板按用户语言偏好自动选择（`PropertiesLoader.loadLocalizedProperties(locale, ...)`）。

### SMTP 配置

运行时配置在 Docker 环境变量文件：

```
docdoku-plm-docker/env/back.env

SMTP_HOST=smtp
SMTP_PORT=1025          ← 默认连 MailHog 测试服务，生产环境需改为 465/587
SMTP_USER=DocDokuPLM
SMTP_FROM_ADDR=noreply@localhost
```

EJB 容器内通过 JNDI 名称 `mail/docdokuSMTP` 注入 `javax.mail.Session`。

---

## 二、账号注册与激活机制

### 注册接口

```
POST /api/accounts/create
→ AccountResource.createAccount()（第 158 行）
→ AccountManagerBean.createAccount()
```

另有 OAuth 注册入口：`AuthResource.java` 第 334 行（OpenID Connect 自动创建账号）。

### 核心逻辑：两种注册策略

`AccountManagerBean.createAccount()` 第 103~110 行根据平台策略决定账号是否立即可用：

```java
OperationSecurityStrategy registrationStrategy = platformOptionsManager.getRegistrationStrategy();
Account account = new Account(pLogin, pName, pEmail, pLanguage, now, pTimeZone);
account.setEnabled(registrationStrategy.equals(OperationSecurityStrategy.NONE));
```

| 策略值 | `enabled` | HTTP 响应 | 效果 |
|--------|-----------|-----------|------|
| `NONE`（默认） | `true` | `200 OK` + JWT token | 注册即可登录 |
| `ADMIN_VALIDATION` | `false` | `202 Accepted` | 需管理员手动启用 |

注册成功后始终发送欢迎邮件（`mailer.sendCredential()`），若账号未启用，邮件内容会包含提示：
> *"Your account is not yet enabled, please contact your platform administrator to enable it"*

### Account 实体字段（数据库表 `ACCOUNT`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `login` | `String`（主键） | 登录名，唯一标识 |
| `name` | `String` | 显示名称 |
| `email` | `String` | 邮件地址 |
| `language` | `String` | 语言偏好（en / zh / fr / ru） |
| `timeZone` | `String` | 时区（默认 Europe/London） |
| `enabled` | `boolean` | **是否已激活/启用** |
| `creationDate` | `Date` | 账号创建时间 |

---

## 三、如果要实现"邮件 Token 自助激活"

> 当前系统**没有**点击邮件链接自动激活的功能，只有管理员审批模式。

若需实现用户自助通过邮件激活账号（减少管理员介入），需改动以下文件：

| 改动点 | 文件 | 工作量 |
|--------|------|--------|
| `Account` 实体加 `activationToken` 字段 | `Account.java` + DB 迁移 | 小 |
| 注册时生成 UUID token 并存入账号 | `AccountManagerBean.java` | 小 |
| 新增发送激活邮件的方法和模板文案 | `NotifierBean.java` + `NotificationText_*.properties` | 小 |
| 新增公开激活接口 `GET /api/accounts/activate?token=xxx` | `AccountResource.java` | 小 |
| 前端注册成功后提示"请查收激活邮件" | `account-creation-form.js` | 小 |
| **总计约 5~8 个文件** | | **中等** |

**如果只是想禁止注册后立即可用**，只需在 Admin 后台把注册策略切为 `ADMIN_VALIDATION`，**零代码改动**。

---

## 四、账号管理：谁能管、在哪管

### 角色体系（三级）

定义在 `UserGroupMapping.java`：

| 角色常量 | 角色 ID | 说明 |
|----------|---------|------|
| `REGULAR_USER_ROLE_ID` | `users` | 普通注册用户 |
| `ADMIN_ROLE_ID` | `admin` | **平台超级管理员**（全局唯一） |
| `GUEST_ROLE_ID` | `guest` | 访客（只读公开内容） |

> 注意：工作空间内还有"工作空间管理员"概念（工作空间创建者），权限仅限其所属工作空间，与平台 `admin` 不同。

### 后端管理接口（全部需要 `admin` 角色）

文件：`AdminResource.java`（类级注解 `@RolesAllowed("admin")`）

| 方法 | 路径 | 功能 |
|------|------|------|
| `GET` | `/api/admin/accounts` | 获取所有账号列表 |
| `PUT` | `/api/admin/accounts` | 更新账号信息 |
| `PUT` | `/api/admin/accounts/{login}/enable?enabled=true/false` | **启用/禁用账号** |
| `PUT` | `/api/admin/platform-options` | **设置注册策略（NONE / ADMIN_VALIDATION）** |
| `GET` | `/api/admin/platform-options` | 查看当前平台策略 |
| `PUT` | `/api/admin/workspace/{workspaceId}/enable` | 启用/禁用工作空间 |
| `GET` | `/api/admin/disk-usage-stats` | 磁盘使用统计 |
| `GET` | `/api/admin/users-stats` | 用户数量统计 |
| `POST/PUT/DELETE` | `/api/admin/providers/...` | 管理 OAuth 提供者 |

### 前端管理页面

登录 `admin` 账号后进入 **Workspace Management** 界面，相关文件：

| 文件 | 功能 |
|------|------|
| `workspace-management/js/views/admin-accounts.js` | 账号列表，支持批量启用/禁用 |
| `workspace-management/js/templates/admin-accounts.html` | 账号管理 HTML 模板 |
| `workspace-management/js/views/admin-options.js` | 平台选项（注册策略配置） |
| `workspace-management/js/views/admin-dashboard.js` | 数据统计仪表盘 |
| `workspace-management/js/views/admin-oauth.js` | OAuth 提供者管理 |

---

## 五、完整注册流程图

```
用户提交注册表单
      │
      ▼
POST /api/accounts/create
      │
      ▼
AccountManagerBean.createAccount()
      ├── 查询 registrationStrategy
      │       ├── NONE → enabled = true
      │       └── ADMIN_VALIDATION → enabled = false
      ├── 写入 ACCOUNT 表（JPA）
      └── mailer.sendCredential() → NotifierBean
                    └── 读取 NotificationText_{lang}.properties
                    └── javax.mail.Transport.send() → SMTP Server

若 enabled = false：
      │
      ▼
管理员登录 Admin 后台
→ Workspace Management → 账号管理
→ 勾选账号 → 点击"启用"
→ PUT /api/admin/accounts/{login}/enable?enabled=true
→ AccountManagerBean.enableAccount()
→ account.setEnabled(true) → JPA 同步到 DB
→ 用户可正常登录
```

---

## 六、平台 admin 角色的提升与降级

### 重要说明

- **任何通过注册接口创建的账号，角色一律是 `users`**，包括登录名叫 `admin` 的账号也不例外。
- 没有任何 UI 或 API 可以将账号提升为 `admin`（调用 Admin 接口本身就要求已是 admin，先有鸡先有蛋）。
- **唯一途径是直接操作数据库**，属于运维级操作。

### 提升为 admin

```bash
docker exec docdoku-plm-docker-db-1 psql -U changeit -d docdokuplm \
  -c "UPDATE usergroupmapping SET groupname = 'admin' WHERE login = '目标登录名';"
```

操作后**必须重启后端容器**，否则 JPA 二级缓存（EclipseLink）会持续返回旧角色，导致登录时 JWT 里仍写入 `users`：

```bash
docker restart docdoku-plm-docker-back-1
# 等待约 40 秒直到后端完全启动
```

重启后，该账号**重新登录**即可获得包含 `admin` 角色的新 JWT token。

> **原因**：角色信息在登录时写入 JWT payload，此后服务端凭 JWT 判断权限，不再查数据库。
> 直接改数据库后若不重启，登录仍从 JPA 缓存读到旧角色，JWT 里 `groupName` 依然是 `users`，前端 `App.config.admin` 为 false，无法进入管理界面。

### 降级为普通用户

```bash
docker exec docdoku-plm-docker-db-1 psql -U changeit -d docdokuplm \
  -c "UPDATE usergroupmapping SET groupname = 'users' WHERE login = '目标登录名';"
```

同样需要重启后端容器后重新登录生效。

### 查看当前所有账号的角色

```bash
docker exec docdoku-plm-docker-db-1 psql -U changeit -d docdokuplm \
  -c "SELECT login, groupname FROM usergroupmapping ORDER BY groupname, login;"
```

### 当前 admin 账号（2026-05-21）

| 登录名 | 角色 |
|--------|------|
| `admin` | `admin` |

> 其余所有账号均为 `users` 角色。

---

## 七、OAuth 提供方

### 作用

OAuth 提供方用于配置**第三方登录**，让用户可以用 Google、GitHub、企业 SSO 等外部账号直接登录 DocDokuPLM，无需单独注册。基于 OpenID Connect（OIDC）协议实现。

目前默认**未配置任何提供方**，登录页只有账号密码方式。

### 管理入口

登录 admin 账号 → Workspace Management → 超级管理员 → **OAuth**

或直接访问：`http://{域名}/workspace-management/index.html#/admin/oauth`

### 配置字段说明

| 字段 | 说明 |
|------|------|
| 名称 | 提供方显示名称，如 `Google`、`GitHub` |
| 发行方（issuer） | OIDC 发行方 URL，如 `https://accounts.google.com` |
| 客户端 ID（clientID） | 在第三方平台注册应用后获得的 App ID |
| 密钥（secret） | 对应的 App Secret |
| 授权端点（authority） | OAuth 授权根 URL |
| JWS 算法 | JWT 签名算法，通常为 `RS256` |
| JWK Set URL | 第三方公钥集地址，服务端用于验证 token 签名 |
| 回调地址（redirectUri） | 登录成功后的回调，固定为 `{站点地址}/callback.html` |
| Scope | 请求的权限范围，通常填 `openid email profile` |
| Response Type | OAuth 响应类型，通常填 `code` |
| 已启用 | 控制登录页是否显示此提供方按钮 |

### 用户登录流程

1. 登录页出现第三方登录按钮（需已启用）
2. 用户点击 → 跳转至第三方授权页面
3. 授权后回调 `callback.html`，携带授权码
4. 后端用授权码换取 token，验证签名（通过 JWK Set URL 获取公钥）
5. 提取用户信息（sub/email），若账号不存在则自动创建（`groupName = users`）
6. 签发本系统 JWT，完成登录

> 通过 OAuth 自动创建的账号同样是 `users` 角色，如需提升为 admin，仍需按第六节的方式操作数据库。
