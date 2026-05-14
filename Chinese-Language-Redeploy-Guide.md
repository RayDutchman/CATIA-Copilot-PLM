# 中文支持生效 —— 重新部署指南

本文档说明：如何让新增的中文（zh）翻译以及本仓库的所有修复，在已运行的 Docker 环境中生效。

---

## 背景：为什么需要重新部署？

`docker-compose.yml` 默认使用 DockerHub 上的预构建镜像：

```yaml
services:
  front:
    image: docdoku/docdoku-plm-front:2.6.2
  back:
    image: docdoku/docdoku-plm-server:2.6.2
```

这些镜像是打包好的，**不会自动感知本地代码变化**。要让中文支持完整生效，需要重新构建后端镜像（方案 B）。

---

## ⚠️ 重要：方案 A 的真实作用范围

### 语言下拉框中"中文"选项从何而来？

Account → Edit account 页面的 **Language 下拉框**，选项列表由**后端 REST API `/languages`** 返回。
预构建的 `docdoku/docdoku-plm-server:2.6.2` DockerHub 镜像**不包含** `zh` 支持，所以即使完成方案 A，下拉框里**仍然没有中文选项**。

### 方案 A 能做什么？

方案 A 通过卷挂载，将本地 `nls/zh/` 翻译文件注入前端容器。它解决的是：**当账户语言已经设置为 `zh` 时，界面能够显示中文文字**。但如果后端不支持 `zh`，账户语言就无法通过 UI 设置为 `zh`，所以：

| 需求 | 方案 A | 方案 B |
|------|--------|--------|
| 界面文字翻译成中文 | ✅ | ✅ |
| Language 下拉框出现"中文"选项 | ❌ | ✅ |
| 注册账号时可以选择中文 | ❌ | ✅ |
| 账户保存语言偏好为中文 | ❌ | ✅ |
| 后端异常消息显示中文 | ❌ | ✅ |

**结论：如果您看到"没有中文选项"，请直接跳到[方案 B](#方案-b完整重建--从源码构建后端镜像推荐)。**

---

## 方案 A：卷挂载（无需编译，仅作辅助）

> 适用场景：已通过方案 B 让后端支持 zh，想避免重建前端镜像时，用此方案注入最新翻译文件。

`docker-compose.yml` 已默认包含以下卷挂载配置，无需手动修改：

```yaml
  front:
    volumes:
      - ./env/front.json:/usr/share/nginx/html/webapp.properties.json
      - ../docdoku-plm-front/app/js/localization/nls:/usr/share/nginx/html/js/localization/nls
```

只需拉取最新代码并重启前端容器即可：

```bash
cd /path/to/CATIA-Copilot-PLM
git pull

cd docdoku-plm-docker
docker compose up --force-recreate --no-deps -d front
```

### 临时体验中文界面（浏览器控制台快捷方式）

如果您只想临时看到中文界面，可以在浏览器开发者工具控制台（F12 → Console）运行以下命令，**无需修改账户设置**：

```javascript
localStorage.setItem('locale', 'zh');
location.reload();
```

> 注意：此方法仅影响当前浏览器，不会保存到账户设置，刷新后需要重新执行。

---

## 方案 B：完整重建 —— 从源码构建后端镜像（推荐）

此方案重新编译后端并打包 Docker 镜像，是让"中文"出现在 Language 下拉框的**唯一正确方式**，包含：

- **`zh` 被加入后端支持的语言列表**（`PropertiesLoader.java`）
- 中文异常消息（`LocalStrings_zh.properties`）
- `pdfbox2-layout` 版本修复（已升至 `1.0.1`，可正常解析依赖）

### 前置条件

| 工具 | 版本要求 | 检查命令 |
|------|----------|----------|
| JDK | 11 | `java -version` |
| Maven | 3.8+ | `mvn -version` |
| Docker | 任意 | `docker --version` |

在 Ubuntu / WSL2 中安装：

```bash
sudo apt-get update
sudo apt-get install -y maven openjdk-11-jdk
```

---

### 第零步：构建基础镜像（首次构建必须）

`docker/Dockerfile` 依赖 `docdoku/docdoku-plm-server-base:2.6.2` 作为基础镜像。该镜像是 DocDoku 公司的私有镜像，**无法从 Docker Hub 公开拉取**（会报 `pull access denied` 错误）。

仓库内已提供构建该基础镜像所需的 Dockerfile，执行一次即可：

```bash
cd /path/to/CATIA-Copilot-PLM/docdoku-plm-server

docker build \
  -f docker/payara/Dockerfile \
  -t docdoku/docdoku-plm-server-base:2.6.2 \
  docker/payara/
```

> ⏱ 此步骤需要下载 Payara 镜像及安装 LibreOffice，首次约 5–20 分钟。
> 构建完成后无需重复执行（除非清空了本地 Docker 镜像缓存）。

---

### 第一步：拉取最新代码

```bash
cd /path/to/CATIA-Copilot-PLM
git pull
```

---

### 第二步：Maven 构建后端

#### 情况 A：首次构建，或修改了语言以外的代码

使用 `install` 目标将所有模块安装到本地 Maven 仓库（`~/.m2`），供后续快速构建使用：

```bash
cd docdoku-plm-server

# 完整构建（跳过测试）——首次约 5–15 分钟，后续有缓存更快
mvn clean install -DskipTests
```

#### 情况 B：仅修改了语言/翻译文件（快速重建）

只需重新构建语言模块（`docdoku-plm-server-i18n`）和装配 EAR，**跳过其他所有模块**，速度大幅缩短：

```bash
cd docdoku-plm-server

# 前提：已执行过一次情况 A 的完整构建（其他模块已在 ~/.m2 中）
mvn clean package -DskipTests \
  -pl docdoku-plm-server-i18n,docdoku-plm-server-ear
```

> ⏱ 快速构建仅重新编译 i18n 模块并重新打包 EAR，通常 1–2 分钟内完成。

构建成功后，关键产物位于：

```
docdoku-plm-server-ear/target/docdoku-plm-server-ear.ear
```

---

### 第三步：构建 Docker 镜像

```bash
# 仍在 docdoku-plm-server/ 目录下执行
docker build \
  --build-arg VERSION=2.6.2 \
  -f docker/Dockerfile \
  -t docdoku/docdoku-plm-server:2.6.2 \
  .
```

> 说明：`docker/Dockerfile` 使用第零步中本地构建的 `docdoku/docdoku-plm-server-base:2.6.2`
> 作为基础镜像，只把本地编译好的 EAR 复制进去。

---

### 第四步：重启后端容器

```bash
cd ../docdoku-plm-docker

# 重建 back 服务，使用刚才本地构建的同名镜像
docker compose up --force-recreate --no-deps -d back
```

---

### 第五步：验证

```bash
# 查看后端启动日志（等待出现 "Deployed" 字样）
docker compose logs -f back
```

启动完成后访问 [http://localhost:8000](http://localhost:8000)，登录后进入
**Account → Edit account → Language**，下拉框中应出现 **中文** 选项，选择并保存，刷新页面即可全程中文显示。

---

## 一键脚本（推荐）

为节省手动操作，`scripts/` 目录已提供三个脚本，授权后直接运行即可：

```bash
# 首次授权（只需一次）
chmod +x scripts/build-base-image.sh scripts/build-backend-full.sh scripts/build-i18n.sh
```

| 脚本 | 用途 | 何时使用 |
|------|------|----------|
| `scripts/build-base-image.sh` | 构建 Payara 基础镜像 | 首次，或清空 Docker 镜像缓存后 |
| `scripts/build-backend-full.sh` | 完整 Maven 构建 + Docker 镜像 + 重部署后端 | 首次，或修改了非语言代码后 |
| `scripts/build-i18n.sh` | 仅重建语言模块 + Docker 镜像 + 重部署后端 | 只修改了翻译/语言文件后 |

**典型首次部署流程：**

```bash
cd /path/to/CATIA-Copilot-PLM

# Step 0（只需一次）
./scripts/build-base-image.sh

# Step 1-4（首次完整构建）
./scripts/build-backend-full.sh
```

**后续仅更新翻译时：**

```bash
cd /path/to/CATIA-Copilot-PLM
./scripts/build-i18n.sh
```

---

## 常用运维命令

```bash
# 查看所有容器状态（需要在 docdoku-plm-docker/ 目录下）
cd /path/to/CATIA-Copilot-PLM/docdoku-plm-docker

docker compose ps

# 查看日志（实时）
docker compose logs -f front
docker compose logs -f back

# 停止所有服务（保留数据）
docker compose down

# 停止并彻底删除所有数据（⚠️ 不可恢复）
docker compose rm --stop --force -v
docker volume rm docdoku-plm-server-volume
```

---

## 语言切换操作步骤

1. 打开浏览器，访问系统首页（默认 [http://localhost:8000](http://localhost:8000)）
2. 登录账号
3. 点击右上角用户头像 → **Account（账户）**
4. 找到 **Language（语言）** 下拉框，选择 **中文**
5. 点击保存
6. **刷新页面**（`Ctrl+F5` / `Cmd+Shift+R`）

> 注册新账号时，注册表单中也有 Language 字段，可以在注册时直接选择中文。

---

## 问题排查

| 现象 | 原因 | 解决方法 |
|------|------|----------|
| Language 下拉框没有"中文"选项 | 后端预构建镜像不支持 zh | **使用方案 B** 从源码重建后端镜像 |
| `pdfbox2-layout:jar:1.0.0` 找不到 | 旧版本 `1.0.0` 未在 JitPack 发布 | 已修复，拉取最新代码后重新构建 |
| `mvn` 报 `Cannot access defaults field of Properties` | `maven-war-plugin:2.2` 与 JDK 17+ 不兼容 | 已修复（`pluginManagement` 中已固定为 `3.3.2`），拉取最新代码后重新构建 |
| `back-1` 日志出现 `CDI deployment failure: Invalid parameter name ""` | 代码编译时未传入 `-parameters` 标志，Weld/CDI 无法读取参数名 | 已修复（`pom.xml` 的 `maven-compiler-plugin` 已加入 `-parameters`），拉取最新代码后重新执行第二、三步构建 |
| `docker build` 报 `pull access denied` for `docdoku-plm-server-base` | 该基础镜像是私有镜像，无法从 Docker Hub 拉取 | 先执行**第零步**，用 `docker/payara/Dockerfile` 在本地构建基础镜像 |
| `docker build` 提示找不到 EAR | Maven 构建未完成或失败 | 检查 `docdoku-plm-server-ear/target/` 目录是否存在 `.ear` 文件 |
| 选了中文但界面仍显示英文 | 前端翻译文件未更新 | 确认 docker-compose.yml 中 nls 卷挂载已生效（方案 A） |
| `docker compose up` 仍使用旧镜像 | Docker 镜像缓存 | 使用 `--force-recreate` 参数强制重建容器 |
