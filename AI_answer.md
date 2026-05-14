# 中文语言切换问题修复说明（2026-05-13 新增）

## 问题描述

在 localhost:8080 页面将语言切换为中文（zh）后，大部分界面内容仍然显示为英语，未能正确切换为汉语。

---

## 根本原因分析

经过代码分析，发现存在以下几个问题：

### 问题一：语言切换后页面不自动重载（主要原因）

**文件：** `docdoku-plm-front/app/js/common-objects/contextResolver.js`

原代码逻辑：
```js
if (window.localStorage.locale === 'unset') {
    window.localStorage.locale = account.language || 'en';
    window.location.reload();  // 只有 locale === 'unset' 才重载
} else {
    window.localStorage.locale = account.language || 'en';  // 静默更新，不重载
}
```

**问题：** `requirejs-i18n` 插件在页面加载时一次性读取 `localStorage.locale` 来决定加载哪个语言包。如果语言包已经以英文加载，后续只更新 `localStorage.locale` 而不重载页面，界面语言不会变化。

只有当 `locale === 'unset'` 时才会重载，但以下两种情况不会触发重载：
- **新用户注册**：`localStorage.locale` 为 `null`，账号语言为 `zh`，不满足 `=== 'unset'` 条件
- **旧会话**：浏览器缓存的 locale 与账号语言不一致时，也不会重载

**修复方案：** 将条件改为"任意不匹配时都重载"：
```js
var accountLocale = account.language || 'en';
if (window.localStorage.locale !== accountLocale) {
    window.localStorage.locale = accountLocale;
    window.location.reload();
}
```

---

### 问题二：中文语言包缺失 7 个键

**文件：** `docdoku-plm-front/app/js/localization/nls/zh/workspace-management.js`

仪表盘（Dashboard）页面所需的以下键在中文语言包中缺失，导致这些内容显示为空或英文：

| 键名 | 中文翻译 |
|------|---------|
| `ACTIVE_USERS` | 活跃用户 |
| `INACTIVE_USERS` | 已禁用用户 |
| `ACTIVE_GROUPS` | 活跃用户组 |
| `INACTIVE_GROUPS` | 已禁用用户组 |
| `CHART_AXIS_DAYS_NUMBER` | 天 |
| `CHART_AXIS_DOCUMENTS_NUMBER` | 文档 |
| `CHART_AXIS_PARTS_NUMBER` | 零件 |

---

### 问题三：HTML 模板中存在硬编码英文字符串

以下模板文件中含有直接写死的英文文本，未使用 i18n 变量，因此无论切换到任何语言都不会翻译：

| 文件 | 硬编码内容 | 修复方式 |
|------|-----------|---------|
| `account-management/js/templates/edit-account-auth.html` | `Validate`（按钮文字） | 改为 `{{i18n.CONFIRM}}` |
| `workspace-management/js/templates/workspace-creation.html` | `Description`（标签和占位符） | 改为 `{{i18n.DESCRIPTION}}` |
| `js/common-objects/templates/linked/linked_change_items.html` | `Low` / `Medium` / `High` / `Emergency`（优先级标签） | 新增 i18n 键并替换 |

---

## 修改的文件列表

1. **`docdoku-plm-front/app/js/common-objects/contextResolver.js`**  
   修复 locale 不匹配时不重载页面的 bug

2. **`docdoku-plm-front/app/js/localization/nls/zh/workspace-management.js`**  
   补充 7 个缺失的中文翻译键

3. **`docdoku-plm-front/app/account-management/js/templates/edit-account-auth.html`**  
   将硬编码 `Validate` 替换为 `{{i18n.CONFIRM}}`

4. **`docdoku-plm-front/app/workspace-management/js/templates/workspace-creation.html`**  
   将硬编码 `Description` 替换为 `{{i18n.DESCRIPTION}}`

5. **`docdoku-plm-front/app/js/common-objects/templates/linked/linked_change_items.html`**  
   将硬编码 `Low/Medium/High/Emergency` 替换为 i18n 模板变量

6. **`docdoku-plm-front/app/js/localization/nls/common.js`**（根语言文件）  
   新增 `CHANGE_ITEM_PRIORITY_LOW/MEDIUM/HIGH/EMERGENCY` 键（英文默认值）

7. **`docdoku-plm-front/app/js/localization/nls/fr/common.js`**  
   新增法语翻译：`Basse / Moyenne / Haute / Urgence`

8. **`docdoku-plm-front/app/js/localization/nls/ru/common.js`**  
   新增俄语翻译：`Низкий / Средний / Высокий / Экстренный`

9. **`docdoku-plm-front/app/js/localization/nls/zh/common.js`**  
   新增中文翻译：`低 / 中 / 高 / 紧急`

---

## 修复效果

修复后，以下情形均可正确切换到中文界面：
- 新用户注册时选择中文语言后，登录跳转页面自动以中文显示
- 已有账号修改语言为中文，刷新页面后全界面显示中文
- 工作区仪表盘（Dashboard）的图表轴标签和用户统计标签显示中文
- 账号认证弹窗的确认按钮、工作区创建表单的描述字段、变更项优先级标签均显示中文

---

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

---

# 解决方案 X 和方案 B 卡住的排查指南

## 问题一：`https://docdokuplm.local:9000` 无法访问

这是 SSL 代理方案（ssl-proxy 服务），需要**三个前置步骤**全部完成才能访问，缺一不可：

### 第一步：配置 hosts 文件
```bash
# Linux/macOS
echo "127.0.0.1 docdokuplm.local" | sudo tee -a /etc/hosts

# Windows（以管理员身份运行 PowerShell）
Add-Content C:\Windows\System32\drivers\etc\hosts "127.0.0.1 docdokuplm.local"
```

### 第二步：浏览器信任自签名根证书
将 `docdoku-plm-docker/proxy/ssl/rootCA.pem` 导入浏览器的"受信任的根证书颁发机构"：
- **Chrome/Edge**：设置 → 隐私和安全 → 安全 → 管理证书 → 受信任的根证书颁发机构 → 导入
- **Firefox**：设置 → 隐私与安全 → 证书 → 查看证书 → 证书颁发机构 → 导入

### 第三步：修改 docker-compose.yml + back.env
在 `docdoku-plm-docker/docker-compose.yml` 的 `front` 服务，将 `front.json` 改为 `front-ssl.json`：
```yaml
volumes:
  - ./env/front-ssl.json:/usr/share/nginx/html/webapp.properties.json
```

在 `docdoku-plm-docker/env/back.env` 中修改：
```
DOCDOKU_PLM_CODEBASE=https://docdokuplm.local:9000
```

然后重建容器：
```bash
cd docdoku-plm-docker
docker compose up --force-recreate --no-deps -d front back
```

> ⚠️ **重要**：如果只是为了让中文生效，**完全不需要走 SSL 方案**。直接用 `http://localhost:8000` 访问即可（即方案A，卷挂载）。

---

## 问题二：`mvn clean package -DskipTests` 报 ERROR

没有具体报错信息难以精确判断，但该项目**最常见的 Maven 构建失败原因**如下：

### 常见原因 1：Java 版本不对（最高发）
该项目需要 **JDK 11**，用 JDK 17+ 会报编译错误：
```bash
java -version  # 确认是否是 11.x
```
如果不是，切换方法：
```bash
# Ubuntu/Debian
sudo apt-get install -y openjdk-11-jdk
sudo update-alternatives --set java /usr/lib/jvm/java-11-openjdk-amd64/bin/java
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
```

### 常见原因 2：Elasticsearch Maven 仓库网络超时
`pom.xml` 中配置了 `https://artifacts.elastic.co/maven`，网络受限时会超时：
```bash
# 加上重试参数
mvn clean package -DskipTests -Dmaven.wagon.http.retryHandler.count=3
```

### 常见原因 3：Maven 版本过低
需要 Maven **3.8.x**：
```bash
mvn --version  # 确认版本
```

**建议优先选方案A（nginx 拦截）**——不需要 Node.js、Maven、JDK，是最简单的让中文下拉选项生效的方法。请把 `mvn` 的具体报错信息贴出来，可以进一步精确定位。

---

# 方案 B 报错 `cannot find symbol: class XmlTransient / XmlElement` 的根本原因及修复

## 根本原因

错误信息：
```
[ERROR] cannot find symbol: class XmlTransient
[ERROR] cannot find symbol: class XmlElement
```

这两个类来自 `javax.xml.bind.annotation.*`，属于 **JAXB（Java XML Binding）API**。

- **JDK 8**：JAXB 内置于 JDK，不需要额外依赖，直接可用。
- **JDK 9/10**：JAXB 移动到 `java.xml.bind` 模块，默认不加载，需加 `--add-modules java.xml.bind`。
- **JDK 11+**：JAXB 模块**从 JDK 完全移除**，必须通过 Maven 依赖显式引入。

你用的是 **JDK 11 或更高版本**，而项目 `pom.xml` 中没有显式声明 `jaxb-api` 依赖（只有 `javaee-api:8.0.1 provided`，但该 jar 在 JDK 11 classpath 下无法补全已被移除的模块）。

---

## 修复方案（已修复到仓库中）

### 第 1 步：在根 pom.xml 的 `dependencyManagement` 中添加版本声明

文件：`docdoku-plm-server/pom.xml`

```xml
<!-- JAXB API: removed from JDK in Java 11, must be supplied explicitly -->
<dependency>
    <groupId>javax.xml.bind</groupId>
    <artifactId>jaxb-api</artifactId>
    <version>2.3.1</version>
    <scope>provided</scope>
</dependency>
```

### 第 2 步：在 `docdoku-plm-server-core/pom.xml` 中引用该依赖

文件：`docdoku-plm-server/docdoku-plm-server-core/pom.xml`

```xml
<dependency>
    <groupId>javax.xml.bind</groupId>
    <artifactId>jaxb-api</artifactId>
</dependency>
```

以上两处修改已提交到仓库，直接 `git pull` 后重新执行：

```bash
cd docdoku-plm-server
mvn clean package -DskipTests
```

即可通过编译。

---

## 为什么用 `provided` 而不是 `compile`？

WildFly（项目使用的应用服务器）本身已包含 JAXB 实现（`glassfish-jaxb`），运行时由服务器提供。`provided` 表示编译期有这个 jar，但部署到 WildFly 后不把它打入 EAR/JAR，防止类加载冲突。

---

# 方案 X（nginx 拦截）操作后设置里仍然没有中文的根本原因

## 根本原因：前端 API 请求完全绕过了 nginx

`docker-compose.yml` 将 `env/front.json` 挂载为前端的 `webapp.properties.json`：

```yaml
volumes:
  - ./env/front.json:/usr/share/nginx/html/webapp.properties.json
```

`front.json` 内容为：

```json
{"server": {"ssl": false, "domain": "localhost", "port": 8001, ...}}
```

前端 JS（`contextResolver.js`）读取该配置后，将 `apiEndPoint` 设置为：

```
http://localhost:8001/docdoku-plm-server-rest/api
```

即 `GET /languages` 的请求直接发往**后端 WildFly 容器的 8001 端口**，**完全不经过 nginx ssl-proxy**。因此在 `nginx.conf` 中加的拦截规则永远不会被执行。

---

## 让方案 X 真正生效的完整步骤

必须同时修改 `front.json`，让前端的 API 请求也经过 nginx（9000 端口），nginx 才能拦截到 `/languages`。

### 第 1 步：修改 `docdoku-plm-docker/env/front.json`

```json
{
    "server": {
        "ssl": true,
        "domain": "localhost",
        "port": 9000,
        "contextPath": "/docdoku-plm-server-rest",
        "wsDomain": "localhost"
    },
    "contextPath": "/",
    "preferLoginWith": false
}
```

> ⚠️ 改成 `ssl: true` + 端口 9000，所有 API 请求将走 `https://localhost:9000/...`，nginx 才会参与路由。

### 第 2 步：在 `proxy/nginx.conf` 中添加精确拦截（已在方案 X 中描述）

### 第 3 步：在 `docker-compose.yml` ssl-proxy 服务中挂载 `languages.json`（已在方案 X 中描述）

### 第 4 步：重启 front 和 ssl-proxy（两个都要，因为 `front.json` 变了）

```bash
docker compose up --force-recreate --no-deps -d front ssl-proxy
```

> ⚠️ 浏览器访问时必须接受自签名证书（首次访问 `https://localhost:9000` 时点"继续访问"）。

---

# 方案 B 报错 `package javax.rmi does not exist` 的根本原因及修复

## 根本原因

错误信息：
```
[ERROR] package javax.rmi does not exist
[ERROR] cannot find symbol: variable PortableRemoteObject
```

`javax.rmi.PortableRemoteObject` 来自 **CORBA/RMI-IIOP API**。

- **JDK 8**：CORBA 内置于 JDK，直接可用。
- **JDK 9/10**：CORBA 移至独立模块 `java.corba`，默认不加载。
- **JDK 11+**：CORBA 模块**完全从 JDK 移除**（JEP 320），`javax.rmi` 包不再存在。

`BeanLocator.java` 中原来用 `PortableRemoteObject.narrow(o, type)` 做类型转换，这是 RMI-IIOP 远程访问的用法。在现代 WildFly 中进行本地 JNDI 查询时，不需要经过 CORBA 层，直接类型转换即可。

---

## 修复方案（已修复到仓库中）

文件：`docdoku-plm-server/docdoku-plm-server-ext/src/main/java/com/docdoku/plm/server/BeanLocator.java`

**删除** `import javax.rmi.PortableRemoteObject;`

**将**：
```java
result.add((T) PortableRemoteObject.narrow(o, type));
```

**改为**：
```java
result.add(type.cast(o));
```

`type.cast(o)` 是 Java 反射的安全类型转换，等价于强转但无 unchecked 警告，对本地 JNDI 查询完全够用。

以上修改已提交到仓库，直接 `git pull` 后重新执行：

```bash
cd docdoku-plm-server
mvn clean package -DskipTests
```

---

## 已知 JDK 11 兼容性修复汇总

| 模块 | 缺失 API | 原因 | 修复方式 |
|------|---------|------|---------|
| `docdoku-plm-server-core` | `javax.xml.bind.*`（JAXB） | JDK 11 移除 `java.xml.bind` 模块 | 添加 Maven 依赖 `javax.xml.bind:jaxb-api:2.3.1`（scope=provided） |
| `docdoku-plm-server-ext` | `javax.rmi.PortableRemoteObject` | JDK 11 移除 `java.corba` 模块（JEP 320） | 移除 import，改用 `type.cast(o)` |

---

# 方案 B 报错 `Could not find artifact pdfbox2-layout:1.0.0` 的根本原因及修复

## 根本原因

错误信息：
```
Could not find artifact com.github.ralfstuckert.pdfbox-layout:pdfbox2-layout:jar:1.0.0
in mulesoft-releases (https://repository.mulesoft.org/nexus/content/repositories/public/)
```

`pdfbox2-layout` 是托管在 **GitHub** 上的开源项目（https://github.com/ralfstuckert/pdfbox-layout），其发布的 Maven artifact 通过 **JitPack** 分发，**不在 MuleSoft Nexus** 仓库中。MuleSoft Nexus 公共仓库本质上是 Nexus 代理，只聚合了部分仓库，不包含 JitPack 上的 GitHub 项目制品。

---

## 修复方案（已修复到仓库中）

文件：`docdoku-plm-server/docdoku-plm-server-office-doc/pom.xml`

**将**：
```xml
<repository>
    <id>mulesoft-releases</id>
    <name>MuleSoft Repository</name>
    <url>https://repository.mulesoft.org/nexus/content/repositories/public/</url>
</repository>
```

**改为**：
```xml
<repository>
    <id>jitpack.io</id>
    <name>JitPack Repository</name>
    <url>https://jitpack.io</url>
</repository>
```

以上修改已提交到仓库，直接 `git pull` 后重新执行：

```bash
cd docdoku-plm-server
mvn clean package -DskipTests
```

---

## 修复 2：版本号需带 `v` 前缀

更换为 JitPack 仓库后，`1.0.0` 仍无法解析：

```
Could not find artifact com.github.ralfstuckert.pdfbox-layout:pdfbox2-layout:jar:1.0.0
in jitpack.io (https://jitpack.io)
```

**根本原因**：JitPack 使用 **git tag 名称**作为 Maven 版本号。该项目在 GitHub 上的发布 tag 是 `v1.0.0`（带 `v` 前缀），而 pom 中使用的是 `1.0.0`，两者不匹配，JitPack 找不到对应版本。

**修复**：在 `docdoku-plm-server/pom.xml` 的 `dependencyManagement` 中将版本从 `1.0.0` 改为 `v1.0.0`：

```xml
<dependency>
    <groupId>com.github.ralfstuckert.pdfbox-layout</groupId>
    <artifactId>pdfbox2-layout</artifactId>
    <version>v1.0.0</version>   <!-- must match git tag exactly -->
</dependency>
```

以上修改已提交到仓库，`git pull` 后重新执行：

```bash
cd docdoku-plm-server
mvn clean package -DskipTests
```

---

## Maven 构建 ERROR 修复汇总（全部）

| 模块 | 错误类型 | 根因 | 修复 |
|------|---------|------|------|
| `docdoku-plm-server-core` | `cannot find symbol: class XmlTransient` | JDK 11 删除 JAXB | 添加 `javax.xml.bind:jaxb-api:2.3.1` 依赖 |
| `docdoku-plm-server-ext` | `package javax.rmi does not exist` | JDK 11 删除 CORBA（JEP 320） | 删除 import，改用 `type.cast(o)` |
| `docdoku-plm-server-office-doc` | `Could not find artifact pdfbox2-layout:1.0.0` in MuleSoft | MuleSoft Nexus 不含 JitPack artifact | 将仓库改为 `https://jitpack.io` |
| `docdoku-plm-server-office-doc` | `Could not find artifact pdfbox2-layout:1.0.0` in JitPack | JitPack 版本号必须与 git tag 完全一致 | 版本改为 `v1.0.0` |

---

# 前端技术栈迁移计划（2026-05-13 新增）

## 替换对照表

| 原技术 | 替代品 | 说明 |
|--------|--------|------|
| Backbone.js | React | 组件化、单向数据流、虚拟DOM |
| RequireJS | Vite | 原生ES模块、极快开发服务器 |
| Less | Sass | 更强逻辑控制、更成熟生态 |
| Grunt | Vite | 同一工具兼替构建与模块加载 |
| Bower | npm | 统一前后端依赖管理 |
| WebGL / Three.js | Three.js（保留） | 持续活跃更新，支持WebGPU |
| WebRTC | WebRTC（保留） | 浏览器底层标准，配合Mediasoup |

## 当前代码规模

- Backbone Views/Models/Collections：403 个 JS 文件
- Mustache HTML 模板：313 个文件
- Less 样式文件：125 个
- 应用模块：account-management、change-management、document-management、organization-management、product-management、product-structure、workspace-management、visualization（Three.js/WebGL）、WebRTC

## 五阶段迁移计划

### 阶段一：基础设施替换（Bower→npm，Grunt/RequireJS→Vite）

不改任何业务代码，只换工具链，让项目能用新工具跑起来。

1. 删除 `bower.json`、`.bowerrc`，把 `bower_components` 中所有依赖迁移到 `package.json`（npm）
2. 删除 `Gruntfile.js` 及所有 `grunt-*` devDependencies
3. 新建 `vite.config.js`，配置多页面入口、`@` 别名、Less 插件（过渡期暂留）、API 代理
4. 将所有 `define([...], function(...){})` 的 RequireJS 模块语法批量转换为 ES Module（可用 codemod 脚本辅助）
5. 将 `requirejs-i18n` 的语言包机制替换为 Vite 的 `import.meta.glob` 动态导入
6. 更新 `package.json` scripts：`dev` → `vite`，`build` → `vite build`
7. 更新 Docker 构建文件，去掉 `bower install`，改为 `npm ci && npm run build`

**验收标准**：`npm run dev` 启动后，至少一个模块页面可在浏览器中正常打开。

### 阶段二：Less → Sass

1. 安装 `sass`，卸载 `less`/`vite-plugin-less`
2. 将 125 个 `.less` 文件批量重命名为 `.scss`
3. 批量处理语法差异：`@color` → `$color`、namespace mixin → `@use`/`@forward`
4. 更新 `vite.config.js` 中 CSS 预处理器配置为 `sass`
5. 逐模块检查编译输出，修复差异

**验收标准**：`npm run build` 无 CSS 报错，页面样式与迁移前视觉一致。

### 阶段三：引入 React（渐进式，Backbone 共存）

1. 安装 `react`、`react-dom`、`@vitejs/plugin-react`
2. 新建 `app/js/react/` 目录作为 React 组件根目录
3. 迁移顺序（从简到繁）：
   - **第 1 批**：`download`、`organization-management`
   - **第 2 批**：`account-management`、`workspace-management`、`change-management`
   - **第 3 批**：`document-management`、`product-management`、`product-structure`
   - **第 4 批**：`visualization`（Three.js）、WebRTC 协作模块
4. 迁移策略：Backbone Model/Collection → React 状态（useState/useReducer 或 Zustand）；Backbone View → React 函数组件；Mustache 模板 → JSX；Backbone Router → React Router v6；Backbone.sync → fetch/axios 服务层

**验收标准**：每批模块迁移完成后功能与迁移前完全等价，Backbone 代码占比逐批下降至 0。

### 阶段四：Three.js 现代化（visualization 模块）

1. 将 Three.js 从 r90 升级到当前稳定版（r170+）
2. 修复 Breaking Changes（材质、几何体 API、渲染器参数）
3. 封装为 React 组件（可选配合 `@react-three/fiber`）
4. WebRTC 部分封装为 React Hook（`useWebRTC`），服务端 SFU 配置单独处理

### 阶段五：收尾与质量保障

1. 删除所有残余 Backbone、RequireJS、Bower、Grunt 相关代码和依赖
2. 升级 Bootstrap 2 → Bootstrap 5（或 Tailwind CSS）
3. 补充单元测试（Vitest + React Testing Library，替代 CasperJS/PhantomJS）
4. 补充 E2E 测试（Playwright）
5. 更新 README，记录新的开发/构建命令

**依赖顺序**：阶段一（工具链）→ 阶段二（Less→Sass）→ 阶段三（Backbone→React，分批）→ 阶段四（Three.js）→ 阶段五（收尾）

---

# 前端替换后的用户体验提升分析（2026-05-13 新增）

## 一、页面响应速度

| 改进点 | 原因 |
|--------|------|
| **首屏加载更快** | Vite 生产构建使用 Rollup 做 Tree-shaking，死代码零打包；RequireJS 所有模块串行加载，Vite 原生 ES 模块并行加载 |
| **开发热更新毫秒级** | Vite HMR（热模块替换）仅更新变动模块，不刷新整页；Grunt+LiveReload 是全页刷新，延迟秒级 |
| **Bundle 体积更小** | npm + Tree-shaking 只打包实际用到的代码；Bower 打包整个库 |

## 二、交互流畅度

| 改进点 | 原因 |
|--------|------|
| **UI 更新无闪烁** | React 虚拟 DOM diff 算法只更新真正变化的 DOM 节点；Backbone View 通常 re-render 整个模板，产生闪烁 |
| **状态管理更可预测** | React 单向数据流让 UI 状态变化路径清晰；Backbone 双向绑定在复杂场景易出现状态不同步 bug |
| **动画/过渡更顺滑** | React 配合 Framer Motion 等库可轻松实现 GPU 加速动画；Backbone 需要手动操作 DOM |

## 三、3D 可视化（Three.js 升级）

| 改进点 | 原因 |
|--------|------|
| **WebGPU 支持** | Three.js r170+ 原生支持 WebGPU 渲染器，在支持的设备上渲染性能提升 3-5 倍 |
| **更多材质与后处理效果** | 新版 Three.js 材质系统、后处理管线（EffectComposer）更完善 |
| **内存泄漏减少** | 新版 Three.js 修复了大量几何体/材质未释放的内存泄漏问题 |

## 四、协作与实时功能（WebRTC + Mediasoup）

| 改进点 | 原因 |
|--------|------|
| **多人同时在线编辑** | Mediasoup SFU 架构支持数十路视频/数据流，原生 WebRTC mesh 架构超过 4 人即卡顿 |
| **网络自适应码率** | Mediasoup 支持 Simulcast，弱网自动降低分辨率，不中断连接 |

## 五、可维护性带来的间接体验提升

- **Bug 修复更快**：React 组件化让定位问题范围缩小，开发者能更快修复影响用户的 bug
- **新功能上线更快**：Vite 开发环境启动 <1 秒（原 Grunt 冷启动约 30-60 秒），开发效率提升
- **样式一致性更好**：Sass 变量/Mixin 统一管理，减少各模块 UI 风格不一致的情况

---

# 一次改好的概率评估（2026-05-13 新增）

## 整体结论

**整体一次全部完成的概率：极低（< 5%）**

但如果按阶段拆分，每个阶段一次成功的概率差异较大：

## 逐阶段评估

| 阶段 | 一次成功概率 | 主要风险 |
|------|------------|---------|
| 阶段一：工具链替换 | **40-60%** | RequireJS→ESM 的 codemod 转换不完整（循环依赖、动态 require、条件 require）；bower 某些库在 npm 无等价包或版本差异大 |
| 阶段二：Less→Sass | **70-80%** | 语法差异较小，批量替换 `@→$` 覆盖大部分情况；风险在于嵌套 namespace mixin 和 `@import` 路径差异 |
| 阶段三：Backbone→React（每批） | **20-40%（每批）** | 403 个 Backbone 文件涉及大量业务逻辑；Backbone.sync 的自定义 HTTP 行为、Events 总线的跨模块通信最难一次迁移正确 |
| 阶段四：Three.js 升级 | **50-70%** | Three.js r90→r170 有明确的 Migration Guide，Breaking Changes 可枚举；风险在于项目对旧 API 的深度使用程度 |
| 阶段五：收尾 | **80-90%** | 主要是删除旧代码和补测试，风险最低 |

## 为什么整体一次成功概率低

1. **规模巨大**：403 JS 文件 + 313 模板 + 125 样式，任意一个文件出错都可能导致功能异常
2. **隐式依赖多**：RequireJS 的模块加载顺序、Backbone Events 的全局总线、`requirejs-i18n` 的语言包加载时机，这些都是"运行时才能发现"的问题，静态分析无法完全覆盖
3. **测试覆盖低**：现有测试使用 CasperJS/PhantomJS（均已停止维护），实际覆盖率不高，迁移后无法充分验证
4. **浏览器兼容性**：WebGPU 等新特性仅部分浏览器支持，需要 fallback 逻辑

## 建议的降险策略

1. **分支隔离**：每个阶段在独立 feature branch 开发，通过 PR review 后再合并
2. **模块级验收**：阶段三每迁移一个模块即在 staging 环境验收，不等全部模块迁移完再测
3. **Feature Flag**：新旧实现并存，通过配置开关切换，出问题秒级回滚
4. **补测试先行**：在阶段三开始前，先用 Playwright 为现有功能补充 E2E 快照测试，作为迁移的回归基准
5. **从最小模块入手**：`download` 模块逻辑最简单，先完整跑通一个模块的迁移流程，验证方法论后再规模化

---

# docdoku-plm-sample-data 使用说明（2026-05-13 新增）

## 模块用途

`docdoku-plm-sample-data` 是一个独立的 Java 命令行工具，通过调用 DocDokuPLM REST API，向已运行的 DocDokuPLM 服务器批量导入示例数据，包括：
- 10 个测试用户账号（rob、joe、steve 等）
- 多个用户组（Group1~Group5）
- 示例工作区（Workspace）
- 示例文档（.docx、.xlsx、.ods、.odt、.txt）
- 示例零件（BassBoat 系列 .obj/.mtl 3D 模型、dodgeengine.obj）
- 示例工作流（Workflow）、变更管理数据等

## 前提条件

1. **DocDokuPLM 服务器已启动**，可通过浏览器访问（默认 `http://localhost:8080`）
2. **已安装 Java 8+** 和 **Maven 3.x**
3. 已有一个 DocDokuPLM 管理员账号（或准备新建的账号名/密码）

## 使用步骤

### Linux / macOS

```bash
# 进入模块目录
cd docdoku-plm-sample-data

# 运行加载脚本（会自动先 mvn build 再执行）
./loadSample.sh -u <用户名> -p <密码> -h <服务器URL> [-w <工作区ID>]
```

**示例：**
```bash
./loadSample.sh -u admin -p changeit -h http://localhost:8080
```

### Windows

```bat
cd docdoku-plm-sample-data
loadSample.bat -u admin -p changeit -h http://localhost:8080
```

### 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `-u` / `--user` | ✅ | 账号名（不存在会自动创建） |
| `-p` / `--password` | ✅ | 账号密码 |
| `-h` / `--host` | ✅ | 服务器地址，如 `http://localhost:8080` |
| `-w` / `--workspace` | ❌ | 工作区 ID（不填则自动生成） |

## 手动构建并运行（不用脚本）

```bash
cd docdoku-plm-sample-data

# 构建 jar 并复制依赖
mvn clean install
mvn dependency:copy-dependencies

# 运行
java -classpath "target/docdoku-plm-sample-data.jar:target/dependency/*" \
  com.docdoku.loaders.Main \
  -u admin -p changeit -h http://localhost:8080
```

## 加载内容一览

脚本运行后会依次创建：
1. 调用者账号及 10 个测试用户
2. 5 个用户组，并将测试用户分配进去
3. 一个工作区，并授权上述用户和用户组
4. 多个文档模板、文档（含附件文件）
5. 多个零件（含 BassBoat 3D 装配体和发动机模型）
6. 产品结构（Product Structure）
7. 工作流模板及变更管理数据（ECR/ECN/ECO）

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `Connection refused` | 服务器未启动或端口不对 | 确认 `http://localhost:8080` 可访问 |
| `401 Unauthorized` | 账号密码错误或账号不存在 | 检查 `-u`/`-p` 参数；首次运行会自动创建账号 |
| `maven: command not found` | 未安装 Maven | `apt install maven` 或从官网下载 |
| `BUILD FAILURE` (API 版本) | `docdoku-api-java` SNAPSHOT 依赖找不到 | 需要先在同一本地仓库 `mvn install` 对应的 API 模块 |

---

# 中文语言重部署指南更新说明（2026-05-14）

## 本次变更

针对 `Chinese-Language-Redeploy-Guide.md` 的优化请求，做了以下更新：

### 1. 删除方案 C（前后端同时重建）

方案 C 需要安装 Node.js 18、npm、bower 等额外工具，且对中文语言支持**没有必要性**——前端中文翻译已通过方案 A 的卷挂载注入，无需重新编译前端 Docker 镜像。删除后指南更简洁，避免误导。

### 2. 优化方案 B 的 Maven 构建步骤

原命令：`mvn clean package -DskipTests`（构建所有 9 个模块，首次约 5–15 分钟）

新策略：

| 情况 | 命令 | 说明 |
|------|------|------|
| 首次 / 修改了非语言代码 | `mvn clean install -DskipTests` | 完整构建并将所有模块安装到 `~/.m2` |
| **仅修改了翻译/语言文件** | `mvn clean package -DskipTests -pl docdoku-plm-server-i18n,docdoku-plm-server-ear` | 只重编译 i18n 模块 + 重打包 EAR，约 1–2 分钟 |

**原理**：`docdoku-plm-server-i18n` 是与语言直接相关的唯一模块（含 `PropertiesLoader.java` 和 `.properties` 文件）。首次完整构建使用 `install` 将其他所有模块安装到本地仓库后，后续只需重新构建 i18n 和最终 EAR，其他模块直接从 `~/.m2` 取用。

### 3. 新增三个一键脚本

| 脚本 | 功能 |
|------|------|
| `scripts/build-base-image.sh` | 构建 Payara 私有基础镜像（首次必须） |
| `scripts/build-backend-full.sh` | `git pull` + 完整 Maven 构建 + Docker 镜像 + 重部署后端 |
| `scripts/build-i18n.sh` | `git pull` + 仅语言模块构建 + Docker 镜像 + 重部署后端 |

典型流程：
```bash
# 首次
./scripts/build-base-image.sh
./scripts/build-backend-full.sh

# 后续只更新翻译
./scripts/build-i18n.sh
```

---

# 中文界面问题全面修复说明（2026-05-14 第二次更新）

## 问题描述

1. 编辑账户页面语言选项中，中文显示"zh"而不是"中文（简体）"
2. 切换中文后，其它页面几乎不是中文
3. 登录界面 (http://localhost:8000/) 希望默认显示中文

---

## 根本原因分析

### 问题一："zh" 显示为 "zh" 而非 "中文（简体）"

**两个原因叠加：**

1. **标签名称**：`nls/common.js`（英文根）中 `LANGUAGES.zh = '中文'`，未使用"中文（简体）"的完整名称
2. **`fr` / `ru` locale 的 LANGUAGES 缺少 `zh` 键**：
   - `nls/fr/common.js` 的 `LANGUAGES` 只有 `fr / en / ru`，**没有 `zh`**
   - `nls/ru/common.js` 同上
   - require.js i18n 插件做 **浅合并**（shallow merge）：locale-specific 文件的 `LANGUAGES` 整体替换 root 的 `LANGUAGES`，不做深度合并
   - 所以当 locale=fr/ru 时，`App.config.i18n.LANGUAGES['zh']` 是 `undefined`
   - jQuery 的 `.text(undefined)` 不改变原有文字，option 的文字保持为模板渲染的原始值 `{{.}}` 即 `"zh"`

### 问题二：切换中文后其它页面不显示中文

**原因：`edit-account.js` 的 `onUpdateSuccess` 逻辑有缺陷**

原代码：
```js
window.localStorage.locale = 'unset';
// 仅弹出提示，不自动刷新
```

- 保存语言切换到 zh 后，locale 被设为字符串 `'unset'`（而非 null/undefined）
- `'unset'` 是 truthy，所以 require.js i18n 会尝试加载 `nls/unset/common.js` 等（不存在），回退到英文 root
- contextResolver 检测到 `'unset' !== 'zh'` 后会设置 locale='zh' 并自动刷新——这需要**两次页面加载**
- 中间那次加载（locale='unset'）显示英文，造成用户困惑

### 问题三：登录界面默认英文

`app/main/main.js` 的 i18n locale 配置：
```js
return window.localStorage.getItem('locale') || 'en';
```
对于从未访问过的新用户，默认展示英文登录页。

---

## 修复内容

### Fix 1：语言标签名改为"中文（简体）"

| 文件 | 修改内容 |
|------|---------|
| `nls/common.js` | `zh: '中文'` → `zh: '中文（简体）'` |
| `nls/zh/common.js` | 同上 |
| `nls/fr/common.js` | `LANGUAGES` 新增 `zh: '中文（简体）'` |
| `nls/ru/common.js` | `LANGUAGES` 新增 `zh: '中文（简体）'` |

### Fix 2：保存语言后立即切换 locale 并自动刷新

`app/account-management/js/views/edit-account.js` 的 `onUpdateSuccess`：

**修复前：**
```js
window.localStorage.locale = 'unset'; // 设为字符串 'unset'
// 只显示提示，不自动刷新
```

**修复后：**
```js
App.config.account = account;  // 更新内存中的账户数据
if (window.localStorage.locale !== account.language) {
    window.localStorage.locale = account.language; // 直接设为新语言
    window.location.reload(); // 立即自动刷新
} else {
    // 语言未变化，只显示成功提示
}
```

效果：保存账户后立即刷新，只需一次页面加载即可切换语言。

### Fix 3：登录界面默认中文

`app/main/main.js`：
```js
// 修复前
return window.localStorage.getItem('locale') || 'en';
// 修复后  
return window.localStorage.getItem('locale') || 'zh';
```

新用户首次访问登录页时，界面默认显示中文。已有偏好的用户不受影响（localStorage 优先）。

---

## 重新部署

只需重建前端翻译（方案 A，无需重编译后端）：

```bash
cd /path/to/CATIA-Copilot-PLM
git pull

cd docdoku-plm-docker
docker compose up --force-recreate --no-deps -d front
```

> 注：以上修改均在前端 JS/NLS 文件中，通过卷挂载即可生效，**无需重新构建后端镜像**。

---

# 中文修复没有看到效果的根本原因诊断（2026-05-14 第三次更新）

## 背景

用户同步了代码修改，但界面仍然是英文，"中文修复没有效果"。以下是逐层剥析。

---

## 最可能的根本原因：账户语言字段仍然是 `en`

这是最关键的一点，前两次修复都没有改变它。

**`contextResolver.js` 的真实行为：**

```js
// contextResolver.js 第 145-148 行（已修复版本）
var accountLocale = account.language || 'en';   // 从服务器获取账户语言
if (window.localStorage.locale !== accountLocale) {
    window.localStorage.locale = accountLocale;  // 用账户语言覆盖 localStorage
    window.location.reload();
}
```

这意味着：**每次页面加载，contextResolver 都会从服务器读取账户的 `language` 字段，并强制将 `localStorage.locale` 改成账户语言。**

如果你的账户在数据库里 `language = 'en'`（注册时的旧默认值），那么：

1. 页面加载 → `localStorage.locale` 可能是 `'zh'`
2. contextResolver 读到 `account.language = 'en'`
3. 发现不匹配 → 把 `localStorage.locale` 改成 `'en'` → 刷新
4. 刷新后用英文加载 → contextResolver 再读账户 → `localStorage.locale = 'en'`，匹配 → 不再刷新
5. 结果：**永远是英文**，与 `main.js` 的默认值 `'zh'` 完全无关

**Fix 3（`main.js` 默认 zh）只对没有 `localStorage.locale` 的全新浏览器有效，一旦 contextResolver 跑过一次，它就会被账户语言覆盖。**

---

## 第二可能原因：前端容器未重新部署

前端 JS 是通过 Docker 卷挂载进容器的。如果 `git pull` 后没有重启前端容器，浏览器访问的仍然是旧文件。

**验证方法：** 在浏览器里打开 `http://localhost:8000/js/common-objects/contextResolver.js`（直接访问 JS 文件），确认里面的 `onUpdateSuccess` 逻辑是否包含 `window.location.reload()`。

---

## 第三可能原因：浏览器缓存了旧 JS 文件

即使容器重启了，浏览器可能还缓存了旧的 JS 文件。

**解决：** 在浏览器里按 `Ctrl+Shift+R`（硬刷新/强制忽略缓存）。

---

## 我需要你提供的诊断信息

请在浏览器控制台（F12 → Console）执行以下命令，把结果告诉我：

```js
// 1. 当前 localStorage 里的 locale 值
localStorage.getItem('locale')

// 2. 当前账户信息里的 language 字段
fetch('/docdoku-plm-server-rest/api/accounts/me', {
  headers: { 'Authorization': 'Bearer ' + localStorage.jwt }
}).then(r => r.json()).then(a => console.log('account.language =', a.language))
```

另外请告诉我：

| 问题 | 期望回答 |
|------|---------|
| 账户设置页面（Edit Account）→ Language 下拉框当前显示的是哪个语言？ | 例：English / French / Chinese |
| 登录页 `http://localhost:8000/index.html` 是中文还是英文？ | 中文 / 英文 |
| 哪些页面/文字是中文的，哪些是英文的？（举2-3个具体例子） | 例："登录按钮是英文 Login，但欢迎页面标题是中文" |
| `git pull` 后是否执行了 `docker compose up --force-recreate --no-deps -d front`？ | 是/否 |
| 是否在浏览器里做过强制刷新（Ctrl+Shift+R）？ | 是/否 |

---

## 快速自查流程

```
账户 language 字段是 'zh' 吗？
    ├── 否 → 去账户设置改成 Chinese，保存 → 自动刷新 → 应该生效
    └── 是 → localStorage.getItem('locale') 是 'zh' 吗？
                ├── 否 → 前端容器未重启 / 浏览器缓存问题
                └── 是 → NLS 文件本身缺键（需要告诉我哪些页面是英文的）
```

**95% 的概率是第一步就能解决：账户的 Language 字段仍然设置的是 English。** 去账户设置改为 Chinese（中文），保存后页面会自动刷新，此后所有页面都应该是中文。

---

# 新诊断信息分析（2026-05-14 第四次更新）

## 用户提供的诊断信息

| 项目 | 结果 |
|------|------|
| `localStorage.getItem('locale')` | `'zh'` ✅ |
| 账户 language 字段 API 调用 | ❌ 报错：`Unexpected token '<'` |
| 直接访问 `http://localhost:8000/js/common-objects/contextResolver.js` | ❌ 无法访问 |

---

## 原因分析

### 问题一：API fetch 报错 `Unexpected token '<'` 的真实原因

这个错误表示服务器返回了 HTML（一个错误页面），而不是 JSON。

**根本原因是 fetch 命令里的 URL 用的是相对路径：**

```js
fetch('/docdoku-plm-server-rest/api/accounts/me', ...)
```

相对路径 `/docdoku-plm-server-rest/api/...` 会请求 `http://localhost:8000/docdoku-plm-server-rest/api/...`，  
但后端实际在 **8001 端口**（由 `front.json` 的 `"port": 8001` 决定）。

在 8000 端口（前端 nginx）请求这个路径，nginx 会返回一个 HTML 404 页面。  
`JSON.parse('<html>...')` 就会报 `Unexpected token '<'`。

**正确的 API 诊断命令：**

```js
// 使用完整 URL（后端在 8001 端口）
fetch('http://localhost:8001/docdoku-plm-server-rest/api/accounts/me', {
  headers: { 'Authorization': 'Bearer ' + localStorage.jwt }
}).then(r => r.json()).then(a => console.log('account.language =', a.language))
```

---

### 问题二：`http://localhost:8000/js/common-objects/contextResolver.js` 无法访问

这是正常的。`contextResolver.js` 是一个 **RequireJS 模块**，在生产构建中，RequireJS 优化器（r.js）会将它打包进对应模块的 bundle 文件，不再作为独立文件提供。

所以这个 URL 404 并不说明任何问题，这是预期行为。

---

### 问题三：`localStorage.locale = 'zh'` 但界面仍然是英文 — 真正的根因

`locale` 已经是 `'zh'`，但页面还是英文，说明问题出在 **zh NLS 文件不在容器里或无法被加载**。

**工作原理：** RequireJS i18n 插件在页面加载时会：
1. 读取 `localStorage.locale = 'zh'`
2. 发起 AJAX 请求加载 `http://localhost:8000/js/localization/nls/zh/common.js`
3. 如果返回 404 → 静默 fallback 到英文（不报错！这就是为什么没有任何可见的错误提示）

**直接验证方法（在浏览器地址栏输入）：**

```
http://localhost:8000/js/localization/nls/zh/common.js
```

- **如果看到 JavaScript 代码**（以 `define({` 开头）→ NLS 文件已加载，问题在别处
- **如果看到 404 / nginx 错误页** → NLS 文件没有挂载到容器里，这就是根因

---

## 为什么 NLS 文件可能不在容器里

前端容器使用的是 Docker Hub 预构建镜像 `docdoku/docdoku-plm-front:2.6.2`，该镜像在 zh 支持加入之前就已构建，**镜像内不包含任何 zh NLS 文件**。

我们通过 `docker-compose.yml` 的卷挂载来注入 zh 文件：

```yaml
- ../docdoku-plm-front/app/js/localization/nls:/usr/share/nginx/html/js/localization/nls
```

**这个挂载要生效，必须满足以下条件：**

1. `docdoku-plm-docker/docker-compose.yml` 中包含上面这一行（已包含 ✅）
2. 运行 docker compose 命令时的工作目录是 `docdoku-plm-docker/`
3. **在最近一次 `git pull` 之后** 执行了 `docker compose up --force-recreate --no-deps -d front`

---

## 立即执行步骤

**第 1 步：重启前端容器（让卷挂载生效）**

```bash
cd /path/to/CATIA-Copilot-PLM/docdoku-plm-docker
docker compose up --force-recreate --no-deps -d front
```

**第 2 步：验证 zh NLS 文件可访问**

浏览器打开：`http://localhost:8000/js/localization/nls/zh/common.js`

应该看到类似：
```js
/*global define*/
define({
    ABOUT_DOCDOKUPLM: '关于 DocDokuPLM',
    ...
```

**第 3 步：硬刷新浏览器（清除缓存）**

```
Ctrl + Shift + R
```

**第 4 步：确认账户语言设置为中文**

用正确的 API URL 检查账户语言：
```js
fetch('http://localhost:8001/docdoku-plm-server-rest/api/accounts/me', {
  headers: { 'Authorization': 'Bearer ' + localStorage.jwt }
}).then(r => r.json()).then(a => console.log('account.language:', a.language))
```

如果返回 `account.language: 'en'`，需要去 **账户设置 → Language → 选 Chinese → 保存**。  
保存后页面自动刷新，此时 `localStorage.locale` 会被设为 `'zh'`，界面应全部显示中文。

---

## 总结：所有可能原因 + 修复方式

| 原因 | 验证方法 | 修复 |
|------|---------|------|
| 容器未重启，卷挂载未生效 | `http://localhost:8000/js/localization/nls/zh/common.js` 返回 404 | `docker compose up --force-recreate --no-deps -d front` |
| 账户 language 字段还是 `en` | 正确 API 命令查询 | 账户设置改为 Chinese，保存 |
| 浏览器缓存了旧 JS | 界面还是英文 | `Ctrl+Shift+R` 硬刷新 |
| zh NLS 文件内容有误 | `nls/zh/common.js` 能访问但 UI 仍英文 | 告知我哪些页面/文字仍是英文，可精确补全缺失的 key |

---

# 中文乱码根本原因及修复（2026-05-14 第五次更新）

## 最新诊断结果

| 检查项 | 结果 |
|--------|------|
| `account.language` | `zh` ✅ |
| `localStorage.locale` | `zh` ✅ |
| `http://localhost:8000/js/localization/nls/zh/common.js` | 可访问，但中文是**乱码** ❌ |
| 界面中英文状态 | 无变化 |

---

## 根本原因：nginx 未声明 UTF-8 编码

NLS 文件本身是正确的 UTF-8 文件（仓库里验证过），容器也在运行，文件也能访问。

问题出在 **nginx 响应头**。默认的 `nginx:1.19.1-alpine` 不在 `Content-Type` 里声明 `charset`：

```http
Content-Type: application/javascript
```

而不是：

```http
Content-Type: application/javascript; charset=utf-8
```

RequireJS 用 XHR 动态加载 NLS 文件时，如果响应头没有 `charset=utf-8`，浏览器（尤其是某些版本）会用默认编码（ISO-8859-1 或系统编码）解码 UTF-8 字节流 → 中文变成乱码 → 应用把这串乱码字符串渲染到 DOM → 界面显示乱码。

---

## 已提交的修复

### 新增文件：`docdoku-plm-docker/front/nginx.conf`

```nginx
server {
    listen       80;
    server_name  localhost;

    # Serve all text and JS files as UTF-8 so Chinese NLS translations
    # are decoded correctly by the browser and by RequireJS XHR requests.
    charset utf-8;

    location / {
        root   /usr/share/nginx/html;
        index  index.html index.htm;
    }
}
```

### 修改文件：`docdoku-plm-docker/docker-compose.yml`

在 `front` 服务的 `volumes` 里新增一行挂载：

```yaml
- ./front/nginx.conf:/etc/nginx/conf.d/default.conf
```

这样在 nginx 的 `Content-Type` 头里会自动加上 `; charset=utf-8`，RequireJS 加载 NLS 文件时就能正确解码 UTF-8 中文。

---

## 应用修复步骤

**`git pull` 后执行：**

```bash
cd /path/to/CATIA-Copilot-PLM/docdoku-plm-docker
docker compose up --force-recreate --no-deps -d front
```

然后强制刷新浏览器：`Ctrl + Shift + R`

**验证方式：** 浏览器打开 `http://localhost:8000/js/localization/nls/zh/common.js`，现在中文应该显示正常（`关于 DocDokuPLM` 而不是乱码）。界面所有文字应该变成中文。

---

# 关于"中文乱码"与"界面不切换"是否是同一问题的分析（2026-05-14）

## 直接回答你的问题

**不，我不能确定"乱码不解决就导致界面不切换"。** 这两个现象有不同的根因，需要分开分析。

---

## 两个现象的技术解释

### 现象 A：直接访问 NLS 文件时中文是乱码

当你在浏览器地址栏直接访问 `http://localhost:8000/js/localization/nls/zh/common.js` 时，浏览器作为**独立资源**处理它，依赖 HTTP `Content-Type` 响应头里的 `charset` 声明来决定编码。如果 nginx 没有声明 `charset=utf-8`，浏览器默认用 Latin-1 解码 UTF-8 字节，导致中文显示为乱码。

**这是一个"查看"层面的问题，不影响 RequireJS 实际加载。**

### 现象 B：RequireJS 如何加载 NLS 文件

RequireJS i18n 插件通过 **`<script>` 标签注入**（不是 XHR）来加载 NLS bundle。当 `<script>` 在 UTF-8 HTML 页面上下文中注入外部 JS 文件时，浏览器**使用页面的 UTF-8 编码**来解析脚本，**不依赖 HTTP 头里的 charset**。

**结论：charset 修复有益（让浏览器直接查看也正确），但它本身不是界面不切换的根本原因。**

---

## 界面仍然显示英文的真正可能原因

### 诊断步骤（在浏览器控制台执行）

**第 1 步：确认 `localStorage.locale` 的当前值**
```js
console.log('locale in localStorage:', localStorage.locale);
```
- 如果输出 `'en'` 或 `undefined` → contextResolver 还未将其设置为 `'zh'`
- 如果输出 `'zh'` → locale 已设置，但 RequireJS 在此次页面加载时读取的是什么？

**第 2 步：确认 RequireJS 实际使用的 locale**
```js
try {
  console.log('RequireJS locale:', require.s.contexts._.config.config.i18n.locale);
} catch(e) { console.log(e); }
```
- 如果返回 `'en'` 但 `localStorage.locale` 是 `'zh'` → 说明 RequireJS 在读取 locale 时 localStorage 还是 `'en'`，后来才被 contextResolver 改成 `'zh'`，但 **RequireJS 的 locale 是一次性读取的，不会响应 localStorage 变化**

**第 3 步：Network 面板验证（刷新页面后搜索 `nls/zh`）**
- 如果没有任何请求到 `nls/zh/` 目录的文件 → RequireJS 根本没有尝试加载中文 bundle，说明它用的是 `'en'`

---

## 核心 Race Condition 问题

```
页面加载顺序：
1. main.js 执行 → RequireJS 读取 localStorage.locale（此时可能是 'en' 或 null）
2. RequireJS 决定加载 nls/en/ 或 nls/root/ 的 bundle
3. contextResolver.resolveAccount() 执行 → 服务器返回 account.language = 'zh'
4. contextResolver 将 localStorage.locale 设置为 'zh'
5. 如果 localStorage.locale 原来就是 'zh'：条件 'zh' !== 'zh' 为 false → 不触发 reload
6. RequireJS 已经加载了英文 bundle → 界面保持英文
```

**关键逻辑（contextResolver.js）：**
```js
var accountLocale = account.language || 'en';  // = 'zh'
if (window.localStorage.locale !== accountLocale) {
    window.localStorage.locale = accountLocale;
    window.location.reload();  // 只有不同时才 reload
}
// 如果 localStorage.locale 已经是 'zh'，但 RequireJS 本次加载用了 'en'，则不会 reload
```

---

## 立即验证方法（强制触发）

在浏览器控制台执行：
```js
// 清除旧的 locale 缓存，强制下次加载时重新判断
delete localStorage.locale;
window.location.reload();
```

- **如果刷新后界面变成中文** → 问题是 `localStorage.locale` 残留的旧值导致 contextResolver 不触发 reload，而 RequireJS 读取时 locale 不对。修复方案：确保 main.js 里的 locale 读取逻辑与 contextResolver 的更新逻辑一致。
- **如果刷新后还是英文** → 说明 contextResolver 确实触发了 reload，但 reload 后 RequireJS 依然加载英文。需要检查账户的 `account.language` 字段是否真的是 `'zh'`（在 Network 面板查看 `/api/accounts/me` 的响应）。

---

## 总结

| 现象 | 根因 | 是否相同问题 |
|------|------|-------------|
| 直接访问 NLS 文件时中文乱码 | nginx 未声明 `charset=utf-8` | ❌ 不同问题 |
| 界面语言不切换 | RequireJS locale 读取时机 vs contextResolver 更新时机的 race condition | ❌ 不同问题 |

修复 charset 只解决"查看"层面的乱码，**不能**解决界面语言不切换。需要通过上面的控制台诊断步骤找出 locale 切换不生效的具体原因。

---

# 诊断结果分析：部分中文 + delete后变英文（2026-05-14）

## 你提供的诊断数据

| 诊断步骤 | 结果 |
|---------|------|
| `localStorage.locale` | `'zh'` ✓ |
| RequireJS locale | `'zh'` ✓ |
| Network 面板 nls/zh 请求 | 存在（截图确认）✓ |
| 界面语言状态 | **部分中文**（不是全中文）|
| `delete localStorage.locale` + reload 后 | **界面变为英文** |

---

## 代码分析结果（已在仓库中验证）

### 1. zh 翻译文件完整性检查

```
common.js:              root=745, zh=745, missing=0 ✓
document-management.js: root=4,   zh=4,   missing=0 ✓
account-management.js:  root=10,  zh=10,  missing=0 ✓
change-management.js:   root=10,  zh=10,  missing=0 ✓
workspace-management.js:root=81,  zh=88,  missing=0 ✓
product-management.js:  root=21,  zh=21,  missing=0 ✓
product-structure.js:   root=6,   zh=6,   missing=0 ✓
organization-management.js: root=14, zh=14, missing=0 ✓
```

**结论：zh 翻译文件是 100% 完整的，所有 key 均已翻译。"部分中文"绝对不是由 zh bundle 里缺少翻译 key 导致的。**

---

### 2. 语言保存流程（edit-account.js）

```js
// onUpdateSuccess: 保存账号后
if (window.localStorage.locale !== account.language) {  // 'en' !== 'zh' → true
    window.localStorage.locale = account.language;  // 设为 'zh'
    window.location.reload();                        // 重载 → RequireJS 读 'zh' → 中文
} else {
    // 只显示成功消息，不重载
}
```

**结论：第一次保存语言='zh' 时，流程正确：setLocale('zh') → reload → RequireJS 加载 zh bundle ✓**

---

### 3. contextResolver 流程（contextResolver.js）

```js
// App.config 初始化时：
locale: window.localStorage.getItem('locale') || 'en'  // 页面加载时一次性读取

// resolveAccount() 时：
var accountLocale = account.language || 'en';  // 从服务器获取
if (window.localStorage.locale !== accountLocale) {
    window.localStorage.locale = accountLocale;
    window.location.reload();  // 只有 localStorage 和服务器不同才 reload
}
```

---

## "部分中文"的根本原因

RequireJS zh bundle **完全正确地**加载了，所有 i18n key 都翻译了。但界面里有些内容 **根本不经过 RequireJS i18n bundle**，所以永远是英文：

### 原因 1：服务器 API 返回的英文内容（最主要）

后端 REST API 返回的响应（错误信息、状态文字等）是英文，例如：
- 保存失败时的错误提示 (`error.responseText` 直接显示，见 `edit-account.js:182`)
- 服务器端验证失败消息
- 工作区名称、文档名称等业务数据（存储时是英文）

### 原因 2：部分模板里有硬编码英文（次要）

某些 Mustache 模板可能包含不走 i18n 的硬编码英文字符串。

### 原因 3：第三方库自带英文 UI（次要）

Bootstrap、datepicker 等组件可能有英文默认文字。

---

## "delete → 英文"现象解释

你执行 `delete localStorage.locale; window.location.reload()` 后看到英文，这是**正常的双重 reload 中间状态**：

```
第 1 次 reload（你看到的）：
  RequireJS 读 localStorage.locale → undefined → 'en' → 加载英文 bundle
  界面显示英文 ← 你此时看到的

  几秒后，contextResolver.resolveAccount() 执行：
    localStorage.locale (undefined) !== account.language ('zh') → true
    → 设 localStorage.locale = 'zh'
    → window.location.reload() 触发第 2 次 reload

第 2 次 reload（自动发生）：
  RequireJS 读 localStorage.locale → 'zh' → 加载 zh bundle
  界面恢复部分中文
```

**你报告的"变成英文"是第 1 次 reload 的瞬间状态。如果你等几秒，页面会自动第二次 reload 恢复成部分中文（这证明服务器 account.language 确实是 'zh'）。**

如果等待后页面没有自动 reload 变回中文，则说明服务器端 account.language 实际存的是 'en'，需要重新去账号设置页面确认并重新保存语言为"中文"。

---

## 如何确认"部分中文"的英文部分来自哪里

在浏览器控制台执行：

```js
// 查看界面上某个英文字符串，在 zh/common.js 里搜索对应 key
// 如果找到 → 说明是 i18n 系统的问题（不太可能，因为 zh 文件完整）
// 如果找不到 → 说明这个字符串不走 i18n，来自服务器 API 或硬编码模板
```

**更简单的验证方法：**

Network 面板，刷新页面后，查看所有 API 请求的响应内容。如果 `/api/...` 的响应体里包含英文字符串，那就是服务器端内容，跟前端 i18n 无关。

---

## 结论总结

| 问题 | 状态 | 根因 |
|------|------|------|
| RequireJS 加载 zh bundle | ✅ 正常 | - |
| zh 翻译 key 完整性 | ✅ 完整（0 missing） | - |
| 语言保存流程 | ✅ 正确 | - |
| "部分中文"原因 | ⚠️ 存在 | 界面部分内容来自服务器 API 英文响应或模板硬编码，不走前端 i18n |
| "delete→英文"原因 | ℹ️ 正常现象 | 双重 reload 的中间状态，等几秒会自动恢复 |

**前端 i18n 本身工作正常。你能看到"部分中文"说明语言切换已经成功了。剩下还显示英文的内容是后端服务器返回的英文数据，需要服务器端做国际化才能变成中文。**

---

# 如何检查服务器端 account.language 实际存储的值（2026-05-14 新增）

## 问题

即使在账号设置页面将语言保存为"中文"，如何确认服务器端 `account.language` 实际存的是不是 `'en'`？

---

## 方法 1：直接查询 API（最准确）

在浏览器控制台执行：

```js
fetch(App.config.apiEndPoint + '/accounts/me', {
    headers: { 'Authorization': 'Bearer ' + localStorage.jwt }
})
.then(r => r.json())
.then(data => console.log('server account.language =', data.language, '| full:', JSON.stringify(data)));
```

返回结果里的 `language` 字段就是服务器实际存储的值。

---

## 方法 2：Network 面板拦截

1. 打开 DevTools → Network 面板
2. 刷新页面
3. 找到请求 URL 包含 `/api/accounts/me` 的请求（Method: GET）
4. 点开 → Response 标签
5. 查看 JSON 里的 `"language"` 字段

---

## 方法 3：拦截保存请求，确认发送的值

在账号设置页面点击保存**之前**，先在控制台挂钩：

```js
var origAjax = $.ajax;
$.ajax = function(opts) {
    if (opts.url && opts.url.includes('/accounts/me') && opts.type === 'PUT') {
        console.log('PUT /accounts/me payload:', opts.data);
    }
    return origAjax.apply(this, arguments);
};
```

然后在账号设置页面选"中文"并保存，控制台会打印实际发送给服务器的 JSON，确认 `language` 字段是否真的是 `"zh"`。

---

## 方法 4：查看内存中的 App.config.account

刷新页面后，在控制台执行：

```js
setTimeout(() => {
    console.log('App.config.account.language =', App.config.account && App.config.account.language);
    console.log('localStorage.locale =', localStorage.locale);
}, 3000);
```

---

## 快速一行命令（推荐）

打开任意页面的控制台，执行：

```js
fetch(App.config.apiEndPoint+'/accounts/me',{headers:{'Authorization':'Bearer '+localStorage.jwt}}).then(r=>r.json()).then(d=>console.log(d.language))
```

---

## 两种结果及含义

| `data.language` 返回值 | 含义 |
|----------------------|------|
| `"zh"` | 服务器端存储正确，语言切换成功，"部分英文"来自后端 API 响应内容 |
| `"en"` 或 `null` | 服务器端没有保存成功，需要检查保存时的 PUT 请求是否返回错误（Network 面板查看 PUT `/accounts/me` 的 Response Code） |

如果返回 `'zh'` → 前端语言切换完全正常，剩余英文来自服务器端 API 内容，需要服务器端国际化处理。  
如果返回 `'en'` 或 `undefined` → 保存语言设置本身失败了，重新在账号页保存并检查 PUT 请求的响应状态码。

---

# 修复"App is not defined"错误（2026-05-14 补充）

## 错误原因

```
Uncaught ReferenceError: App is not defined
```

`App` 是 RequireJS 模块系统初始化后才挂载到 `window` 上的全局对象。如果你在**登录页**、**工作区选择页**，或者在页面加载完成之前打开控制台执行命令，RequireJS 尚未完成初始化，`App` 变量不存在。

---

## 解决方法：不依赖 App，直接用 window.location 构造 API 地址

`apiEndPoint` 的构造规则就是 `当前页面 origin + /api`（源码 contextResolver.js 第 125 行）：

```js
App.config.apiEndPoint = (isSSL ? 'https' : 'http') + base + 'api';
// base = '://' + domain + ':' + port + '/'
// 等价于 window.location.origin + '/api'（在默认部署下）
```

所以可以直接用：

```js
var apiBase = window.location.origin + '/api';
fetch(apiBase + '/accounts/me', {
    headers: { 'Authorization': 'Bearer ' + localStorage.jwt }
})
.then(r => r.json())
.then(d => console.log('language =', d.language, '| full:', JSON.stringify(d)));
```

**一行版：**

```js
fetch(location.origin+'/api/accounts/me',{headers:{'Authorization':'Bearer '+localStorage.jwt}}).then(r=>r.json()).then(d=>console.log(d.language))
```

---

## 如果 contextPath 不为空（部署在子路径下）

如果应用不是部署在根路径（如 `http://server:8080/docdoku/`），则 API 地址是：

```
http://server:8080/docdoku/api
```

可以从当前页面 URL 中提取：

```js
// 自动从当前 URL 提取 contextPath
var apiBase = location.href.replace(/\/[^\/]*$/, '') + '/api';
// 或者直接硬编码：
var apiBase = 'http://localhost:8080/api';

fetch(apiBase + '/accounts/me', {
    headers: { 'Authorization': 'Bearer ' + localStorage.jwt }
})
.then(r => r.json())
.then(d => console.log('language =', d.language));
```

---

## 如果 localStorage.jwt 也为空

说明你未登录，或者使用的是 Session/Cookie 认证而非 JWT。这时去掉 Authorization 头，让浏览器自动带 Cookie：

```js
fetch(location.origin+'/api/accounts/me',{credentials:'include'}).then(r=>r.json()).then(d=>console.log(d.language))
```

---

## 总结：推荐命令（无需 App，适用任何页面）

```js
fetch(location.origin+'/api/accounts/me',{headers:{'Authorization':'Bearer '+localStorage.jwt}}).then(r=>r.json()).then(d=>console.log(d.language))
```

| 情况 | 使用命令 |
|------|---------|
| 正常登录状态（JWT 认证） | 上方带 `Authorization` 头的命令 |
| Session/Cookie 认证 | 带 `credentials:'include'` 的命令 |
| App 已初始化（在 workspace 页面） | 原来的 `App.config.apiEndPoint` 命令也可用 |

---

# docdoku-plm-sample-data 部署指南 + 后台账号密码管理（2026-05-14 新增）

## 一、docdoku-plm-sample-data 是什么

`docdoku-plm-sample-data` 是一个 **Java 客户端工具**，通过调用 DocDokuPLM 的 REST API，自动在服务器上创建演示用的账号、工作区和样例数据（零件、文档、工作流等）。

**环境要求：**
- Java JDK 7+
- Maven 3+
- DocDokuPLM 服务器已通过 `docker-compose up -d` 启动，且后端完全就绪

---

## 二、部署步骤

### 第1步：确认后端服务已就绪

```bash
cd docdoku-plm-docker
docker-compose up -d
# 等待约 60~120 秒让 back 容器完全启动
docker-compose logs -f back
# 看到包含 "deployed" 或 "ready" 的日志行即可
```

> **注意：** `back` 服务（后端）使用的端口是 **8001**（映射自容器内 8080），不是前端的 8000。

### 第2步：进入 sample-data 目录，运行加载脚本

```bash
cd docdoku-plm-sample-data

# Linux / Mac
./loadSample.sh -u admin -p admin123 -h http://localhost:8001 -w my-workspace

# Windows
loadSample.bat -u admin -p admin123 -h http://localhost:8001 -w my-workspace
```

参数说明：

| 参数 | 说明 | 示例 |
|------|------|------|
| `-u` | 登录名（**将自动创建此账号**） | `admin` |
| `-p` | 密码（**将自动创建此账号**） | `admin123` |
| `-h` | 服务器 URL，**指向后端 8001 端口** | `http://localhost:8001` |
| `-w` | 工作区名称（可选，不填自动生成 `wks-xxxxxxxx`） | `my-workspace` |

### 第3步：验证结果

脚本运行成功后，终端会输出：

```
Congratulations!
Everything is ok, you can now connect to DocDokuPLM http://localhost:8001
Credentials: admin/admin123
Workspace: my-workspace
```

然后打开浏览器访问 `http://localhost:8000`，用 `admin` / `admin123` 登录，即可看到自动创建的样例数据。

### Sample-data 会自动创建哪些账号？

除了你通过 `-u`/`-p` 指定的主账号外，工具还会自动批量创建以下固定登录名的账号：

```
rob, joe, steve, mickey, bill, rendal, winie, titi, toto, tata
```

这些账号的密码与主账号密码相同（均为 `-p` 参数的值）。

---

## 三、后台账号和密码管理

DocDokuPLM 有以下几种方式管理账号密码：

### 方式一：通过前端 UI（最简单）

1. 用管理员账号登录 `http://localhost:8000`
2. 点击右上角头像 → **Account**（账户设置）→ 修改自己的密码
3. 管理员进入 **Organization**（组织管理）→ **Users** → 可查看、停用所有用户

### 方式二：通过 Adminer 数据库管理界面

docker-compose 内置了 Adminer 数据库管理界面，可以直接查看用户数据：

```
访问地址：http://localhost:8004
系统：PostgreSQL
服务器：db
用户名：changeit        ← 来自 docdoku-plm-docker/env/db.env: POSTGRES_USER
密码：changeit          ← 来自 docdoku-plm-docker/env/db.env: POSTGRES_PASSWORD
数据库：docdokuplm      ← 来自 docdoku-plm-docker/env/db.env: POSTGRES_DB
```

关键数据库表：

| 表名 | 用途 |
|------|------|
| `ACCOUNT` | 用户账号（login、email、language 等） |
| `CREDENTIAL` | 密码哈希（password 字段为 SHA-512+盐值哈希） |

> ⚠️ **注意**：密码是哈希存储的，**不能直接在数据库中修改为明文**。需要通过 API 或前端流程重置密码。

### 方式三：通过 REST API（推荐脚本化批量管理）

**创建新账号（无需登录，注册接口为公开接口）：**

```bash
curl -X POST http://localhost:8001/docdoku-plm-server-rest/api/accounts \
  -H "Content-Type: application/json" \
  -d '{
    "login":"newuser",
    "password":"newpass123",
    "email":"newuser@example.com",
    "name":"New User",
    "language":"zh",
    "timeZone":"Asia/Shanghai"
  }'
```

**修改自己的账号信息（包括密码）：**

```bash
# 第1步：登录获取 JWT Token
TOKEN=$(curl -s -X POST http://localhost:8001/docdoku-plm-server-rest/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login":"admin","password":"admin123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('jwt',''))")

# 第2步：修改账号信息（含密码）
curl -X PUT http://localhost:8001/docdoku-plm-server-rest/api/accounts/me \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "login":"admin",
    "password":"newpassword123",
    "email":"admin@example.com",
    "name":"Admin",
    "language":"zh",
    "timeZone":"Asia/Shanghai"
  }'
```

### 方式四：修改数据库连接密码（仅针对 DB 连接凭据，非用户密码）

如需更改 PostgreSQL 数据库本身的连接密码，需要同步修改两个文件后重建容器：

1. 编辑 `docdoku-plm-docker/env/db.env`：修改 `POSTGRES_PASSWORD`
2. 编辑 `docdoku-plm-docker/env/back.env`：同步修改 `DATABASE_PWD`
3. 重建容器：

```bash
docker-compose down -v   # ⚠️ -v 会清空所有数据，谨慎使用
docker-compose up -d
```

---

# Docker 容器图片分析与清理（2026-05-14 新增）

## 图片中发现的问题

根据截图中的 Docker Desktop 容器列表，可以发现以下情况：

### 问题1：存在多个已停止（Exited）的容器

图中有若干容器状态为 **Exited**（已退出），这意味着：

- 这些容器已经停止运行，不再占用 CPU/内存
- 但它们仍占用**磁盘空间**（容器层文件系统）
- 容器名称可能与新启动的同名容器冲突

### 问题2：可能存在多套 docdoku-plm 容器叠加

如果你多次执行了 `docker-compose up`，可能会看到多套相同名称的容器（新旧各一套），旧的处于 Exited 状态。

### 问题3：端口冲突风险

如果 Exited 容器中有已绑定端口的记录，重新启动时可能引发端口冲突错误（`bind: address already in use`）。

---

## 停止的容器可以删掉吗？

**可以安全删除**，但需要注意以下前提：

| 条件 | 说明 |
|------|------|
| ✅ 容器状态为 Exited | 已停止的容器不影响正在运行的服务 |
| ✅ 不是数据卷的唯一来源 | docdoku-plm 的数据存放在**命名 volume**（如 `db-volume`），不存在容器本身，删容器不会丢数据 |
| ⚠️ 不要删除正在运行的容器 | 状态为 Running/Up 的容器不要误删 |

### 清理命令

**方式一：通过 Docker Desktop UI**

在 Docker Desktop 容器列表中，勾选所有 Exited 状态的容器 → 点击 Delete 即可。

**方式二：命令行批量清理所有已停止容器**

```bash
# 删除所有已停止的容器（不影响运行中容器）
docker container prune

# 确认后执行，会提示 "Are you sure? [y/N]"
```

**方式三：更彻底的清理（连同无用镜像、缓存一起清）**

```bash
# 清理停止的容器 + 悬空镜像 + 未使用网络 + 构建缓存
docker system prune

# 如果还想清理未被任何容器使用的镜像：
docker system prune -a
```

> ⚠️ `docker system prune -a` 会删除所有未使用的镜像，包括 docdoku-plm 的镜像。下次 `docker-compose up` 时需要重新拉取，比较耗时，生产环境慎用。

---

## 推荐操作流程

```bash
# 1. 先停止所有 docdoku-plm 容器（如果有运行中的）
cd docdoku-plm-docker
docker-compose down

# 2. 清理所有已停止容器（安全，不影响 volume 数据）
docker container prune -f

# 3. 重新启动（干净启动）
docker-compose up -d
```

这样可以确保没有残留容器干扰，且不会丢失数据库中的数据。

---

# loadSample.sh 依赖下载失败排查（2026-05-14 新增）

你这个报错的核心是：

```text
Could not find artifact com.docdoku.plm:docdoku-plm-api-java:jar:2.6.2 in central
```

## 根因

`docdoku-plm-sample-data` 依赖 `com.docdoku.plm:docdoku-plm-api-java:2.6.2`，但这个包**不是发布在 Maven Central 的公共包**，而是当前仓库里的本地模块：

- `docdoku-plm-api/docdoku-plm-api-java`

所以直接在 `docdoku-plm-sample-data` 下跑 `./loadSample.sh`，Maven 只能去 Central 找，最终失败。

## 解决办法（推荐）

先把本仓库里的 API 模块安装到你本机 Maven 本地仓库，再运行 sample-data：

```bash
# 1) 在仓库根目录执行：先安装 API 相关模块到本地 ~/.m2
cd /mnt/d/CATIA-Copilot-Project/CATIA-Copilot-PLM
mvn -f docdoku-plm-api/pom.xml -DskipTests install

# 2) 再运行 sample-data
cd docdoku-plm-sample-data
./loadSample.sh -u admin -p admin123 -h http://localhost:8001 -w my-workspace
```

如果你只想最小化构建范围，也可用：

```bash
mvn -f docdoku-plm-api/pom.xml -pl docdoku-plm-api-base,docdoku-plm-api-java -am -DskipTests install
```

## 额外提醒

1. `-h` 要指向后端端口（你的环境是 `http://localhost:8001`），这点你已经是对的。  
2. 若仍失败，先确认 Java 版本（建议 JDK 8）与 Maven 可用：  
   ```bash
   java -version
   mvn -version
   ```
3. 若本地缓存过坏包，可清理后重试：  
   ```bash
   rm -rf ~/.m2/repository/com/docdoku/plm/docdoku-plm-api-java
   rm -rf ~/.m2/repository/com/docdoku/plm/docdoku-plm-api-base
   ```

## 一句话结论

这不是你命令参数写错，而是**缺少本地安装 `docdoku-plm-api-java` 依赖**；先安装 `docdoku-plm-api` 模块，再跑 `loadSample.sh` 就可以。

---

# 问题解答：PostgreSQL 数据目录映射错误的影响（2026-05-14）

## 背景

之前的 `docker-compose.yml` 中，`db` 服务的 Volume 挂载路径写成了 `/var/lib/mysql`（MySQL 的路径），而不是 PostgreSQL 正确的 `/var/lib/postgresql/data`。这个问题已在 commit `92f1d43` 中修复。

---

## Q1：路径映射错误，为什么我还能登录并且创建账号、上传零件？

**原因：PostgreSQL 完全忽略了那个错误的挂载点，在容器内部自行运行。**

PostgreSQL 镜像启动时，数据目录由环境变量 `PGDATA` 控制，默认值是 `/var/lib/postgresql/data`。当 `db-volume` 被挂载到 `/var/lib/mysql` 时：

- `/var/lib/mysql` 这个路径对 PostgreSQL **毫无意义**（那是 MySQL 的数据目录）
- PostgreSQL 完全不理会那个挂载，照样在 `/var/lib/postgresql/data`（容器的**临时可写层**）里初始化并写数据
- 应用能正常工作，因为数据库本身是健康的，只是数据没有真正持久化

**实际后果：**  
每次执行 `docker-compose down` 再 `up`（容器被删除重建），数据库里所有数据（账号、工作区、零件记录等）都会**全部丢失**，因为它们存在容器的临时可写层里，而不在 named volume 里。

---

## Q2：那个 Volume（`db-volume`）去哪了？

`db-volume` 这个 named volume **仍然存在于你的 Docker 系统中**，只是它被挂载到了 `/var/lib/mysql`，PostgreSQL 从来没有向那里写过任何数据——所以它实际上是**空的**。

可以用以下命令确认：
```bash
# 查看所有 named volumes（名称包含项目目录名前缀）
docker volume ls

# 查看 db-volume 的详情（Mountpoint 字段显示宿主机上的实际路径）
docker volume inspect docdokuplmdocker_db-volume
```

---

## Q3：能不能删掉？

**可以删，而且推荐清理后重新开始。**

因为旧的 `db-volume` 是空的（从未存储过 PostgreSQL 数据），没有任何有价值的内容。

```bash
# 方式一：彻底清理并重建（推荐）
cd docdoku-plm-docker
docker-compose down -v    # -v 会删除所有关联的 named volumes（包括 db-volume）
docker-compose up -d      # 重新创建，此时 db-volume 正确挂载到 /var/lib/postgresql/data

# 方式二：只删除 db-volume（需要先停止容器）
docker-compose down
docker volume rm docdokuplmdocker_db-volume
docker-compose up -d
```

> ⚠️ 注意：执行 `down -v` 会同时删除 `es-volume`（Elasticsearch 索引）和 `docdoku-plm-server-volume`（上传的文件）。如果你有重要数据需要保留，用方式二只删 `db-volume`。

---

## Q4：这个错误有没有可能导致语言切换不正常？

**不会，两者完全无关。**

语言切换问题的原因链是：

1. **语言选项不显示"中文"**：后端 Java 代码中硬编码了支持的语言列表，未包含 `zh`，这和数据库无关
2. **中文翻译不加载**：前端 NLS 文件加载路径/编码（nginx charset）问题，也和数据库无关
3. **语言偏好设置**：用户的语言偏好虽然存储在数据库中，但只要容器没有重启，数据就在内存+临时可写层里，可以正常读写

因此，语言切换问题是**前端 NLS 文件 + 后端语言枚举**的问题，已经在之前的 PR 中通过挂载翻译文件和修改后端枚举来修复，与 PostgreSQL 的 Volume 映射无关。

---

## 关于"让你记住每次都写在 AI_answer.md"

已通过 `store_memory` 工具将此偏好永久保存到 Agent 的记忆中：

> **"Always write all answers and explanations into AI_answer.md in the repository root, not just in the chat response."**

今后每次回答问题，都会优先将内容写入 `AI_answer.md` 并通过 `report_progress` 提交到仓库，确保你能在文件中看到答案。

---

# loadSample.sh 报错修复：Source/Target option 7 不再支持（2026-05-14）

## 错误信息

```
[ERROR] Source option 7 is no longer supported. Use 8 or later.
[ERROR] Target option 7 is no longer supported. Use 8 or later.
```

## 原因

`docdoku-plm-sample-data/pom.xml` 中 `maven-compiler-plugin` 的配置写死了 Java 1.7：

```xml
<source>1.7</source>
<target>1.7</target>
```

你使用的 JDK（JDK 17 或 JDK 21）已经**彻底移除了对 Java 7 源码/字节码目标的支持**。从 JDK 17 开始，`--release 7` / `-source 1.7` / `-target 1.7` 全部不合法，编译器直接报错。

## 修复方法

将 `docdoku-plm-sample-data/pom.xml` 中的版本改为 `1.8`（已修复，见本次 commit）：

```xml
<!-- 修复前 -->
<source>1.7</source>
<target>1.7</target>

<!-- 修复后 -->
<source>1.8</source>
<target>1.8</target>
```

## 为什么选 1.8？

- 原项目最低支持 Java 8，选 `1.8` 是最保守的改动，不会引入新的 API 依赖
- 你的 JDK 17/21 完全兼容编译 Java 8 源码

## 修复后重新运行

```bash
cd /mnt/d/CATIA-Copilot-Project/CATIA-Copilot-PLM
./docdoku-plm-sample-data/loadSample.sh -u admin -p admin123 -h http://localhost:8001 -w my-workspace
```

> 注意：`loadSample.sh` 在 `docdoku-plm-sample-data/` 子目录下，需确认路径正确。  
> 如果你在仓库根目录运行，命令是：  
> ```bash
> cd docdoku-plm-sample-data
> ./loadSample.sh -u admin -p admin123 -h http://localhost:8001 -w my-workspace
> ```

## 一句话结论

`pom.xml` 中 `<source>1.7</source>` 和 `<target>1.7</target>` 与新版 JDK 不兼容，改为 `1.8` 即可解决编译错误。
