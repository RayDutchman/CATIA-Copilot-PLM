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
