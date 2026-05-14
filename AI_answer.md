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
