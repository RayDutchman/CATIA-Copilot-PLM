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

这些镜像是打包好的，**不会自动感知本地代码变化**。要让以下修改生效，需要重新构建镜像：

- 前端：新增的 `nls/zh/` 中文翻译文件
- 后端：`LocalStrings_zh.properties` 中文异常消息，以及 `pdfbox2-layout` 版本修复（`1.0.0` → `1.0.1`）

有两种方案，按需选择：

---

## 方案 A：快速方案 —— 卷挂载（仅前端中文，无需编译）

此方案通过 Docker 卷挂载，将本地 `nls/` 目录直接注入前端容器，覆盖镜像内的文件。**不需要安装 Node.js / Maven / JDK**，几分钟内生效。

> ⚠️ 局限：后端异常消息（权限错误等）因为编译进了 JAR，仍会显示英文。如需后端也显示中文，请用方案 B。

### 第一步：拉取最新代码

```bash
cd /path/to/CATIA-Copilot-PLM
git pull
```

### 第二步：修改 docker-compose.yml

打开 `docdoku-plm-docker/docker-compose.yml`，在 `front` 服务的 `volumes` 下**新增一行**：

```yaml
  front:
    image: docdoku/docdoku-plm-front:2.6.2
    networks:
      - network
    ports:
      - 8000:80
    volumes:
      - ./env/front.json:/usr/share/nginx/html/webapp.properties.json
      # 新增下面这一行，挂载中文翻译文件
      - ../docdoku-plm-front/app/js/localization/nls:/usr/share/nginx/html/js/localization/nls
```

> `../docdoku-plm-front/app/js/localization/nls` 是相对于 `docdoku-plm-docker/` 目录的路径。
> 如果您的目录结构不同，请替换为绝对路径。

### 第三步：重新创建前端容器

```bash
cd docdoku-plm-docker

# 仅重建 front 服务（不影响其他容器和数据）
docker compose up --force-recreate --no-deps -d front
```

### 第四步：验证

打开浏览器访问 [http://localhost:8000](http://localhost:8000)，登录后进入
**Account → Edit account → Language**，选择 **中文** 并保存，刷新页面即可全程中文显示。

---

## 方案 B：完整重建 —— 从源码构建后端镜像（推荐）

此方案重新编译后端并打包 Docker 镜像，包含：

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

### 第一步：拉取最新代码

```bash
cd /path/to/CATIA-Copilot-PLM
git pull
```

### 第二步：Maven 构建后端

```bash
cd docdoku-plm-server

# 编译并打包 EAR（跳过测试，加快速度）
mvn clean package -DskipTests
```

构建成功后，关键产物位于：

```
docdoku-plm-server-ear/target/docdoku-plm-server-ear.ear
```

> ⏱ 首次构建需要下载依赖，约 5–15 分钟；后续会使用本地缓存，速度更快。

### 第三步：构建 Docker 镜像

```bash
# 仍在 docdoku-plm-server/ 目录下执行
docker build \
  --build-arg VERSION=2.6.2 \
  -f docker/Dockerfile \
  -t docdoku/docdoku-plm-server:2.6.2 \
  .
```

> 说明：`docker/Dockerfile` 使用 DockerHub 上已有的 `docdoku/docdoku-plm-server-base:2.6.2`
> 作为基础镜像（无需手动构建 payara 层），只把本地编译好的 EAR 复制进去。

### 第四步：重启后端容器

```bash
cd ../docdoku-plm-docker

# 重建 back 服务，使用刚才本地构建的同名镜像
docker compose up --force-recreate --no-deps -d back
```

### 第五步：验证

```bash
# 查看后端启动日志（等待出现 "Deployed" 字样）
docker compose logs -f back
```

启动完成后访问 [http://localhost:8000](http://localhost:8000)，语言切换方式同方案 A。

---

## 方案 C：前后端同时重建（完整中文支持）

如果同时需要重建前端（含 npm 构建），请在方案 B 的基础上，**先**完成前端构建：

### 前置条件（额外）

| 工具 | 版本要求 | 检查命令 |
|------|----------|----------|
| Node.js | 18+ | `node --version` |
| npm | 随 Node | `npm --version` |

安装 Node.js 18：

```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### 构建前端

```bash
cd /path/to/CATIA-Copilot-PLM/docdoku-plm-front

npm install
npx bower install --allow-root

# 构建并打包 Docker 镜像（脚本内含 docker build）
./build.sh
```

> 构建完成后执行 `docker images | grep docdoku-plm-front` 确认镜像已生成。

然后按方案 B 的步骤构建后端，最后重启前后端：

```bash
cd ../docdoku-plm-docker
docker compose up --force-recreate --no-deps -d front back
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

1. 打开浏览器，访问系统首页
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
| `pdfbox2-layout:jar:1.0.0` 找不到 | 旧版本 `1.0.0` 未在 JitPack 发布 | 已修复，拉取最新代码后重新构建 |
| `docker build` 提示找不到 EAR | Maven 构建未完成或失败 | 检查 `docdoku-plm-server-ear/target/` 目录是否存在 `.ear` 文件 |
| 容器启动后语言列表无中文 | 前端镜像未更新 | 使用方案 A 挂载卷，或用方案 C 重建前端镜像 |
| `docker compose up` 仍使用旧镜像 | Docker 镜像缓存 | 使用 `--force-recreate` 参数强制重建容器 |
