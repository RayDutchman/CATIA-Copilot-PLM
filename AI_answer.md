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
