# 中文支持生效 —— 重新部署指南

本文档说明：如何让新增的中文（zh）翻译在您已经运行的 Docker 环境中生效。

---

## 背景：为什么需要重新部署？

当前 `docker-compose.yml` 使用的是 DockerHub 上预构建的镜像：

```yaml
services:
  front:
    image: docdoku/docdoku-plm-front:2.6.2
  back:
    image: docdoku/docdoku-plm-server:2.6.2
```

这些镜像是打包好的，**不会自动感知本地代码变化**。要让中文翻译生效，需要让容器使用到新添加的 `nls/zh/` 文件以及更新后的后端 `.properties` 文件。

有两种方案，选择其中一种即可：

---

## 方案 A：快速方案 —— 卷挂载（推荐，无需重新构建镜像）

此方案通过 Docker 卷挂载，直接将本地的 `nls/` 目录注入到运行中的前端容器，覆盖镜像内的文件。**不需要安装 Node.js / Maven / Java**。

后端异常消息（如权限错误提示等）因为编译进了 JAR，仍会显示英文；但界面所有 UI 文字均可切换为中文。

### 第一步：拉取最新代码

```bash
# 进入项目根目录（请替换为您实际的路径）
cd /path/to/CATIA-Copilot-PLM

git pull
```

### 第二步：修改 docker-compose.yml

打开 `docdoku-plm-docker/docker-compose.yml`，找到 `front` 服务，在其 `volumes` 下**新增一行**挂载：

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

> ⚠️ `../docdoku-plm-front/app/js/localization/nls` 是相对于 `docdoku-plm-docker/` 目录的路径，指向仓库中的 `docdoku-plm-front/app/js/localization/nls`。如果您的目录结构不同，请替换为绝对路径。

### 第三步：重新创建前端容器

```bash
cd docdoku-plm-docker

# 仅重建 front 服务（不影响其他容器和数据）
docker compose up --force-recreate --no-deps -d front
```

### 第四步：验证

打开浏览器访问 [http://localhost:8000](http://localhost:8000)（或您配置的端口），登录后进入 **Account → Edit account**，在 **Language** 下拉菜单中即可看到 **中文** 选项。选择后保存，刷新页面即可全程中文显示。

---

## 方案 B：完整重建 —— 从源码构建镜像

此方案重新构建前后端 Docker 镜像，中文支持最完整（包括后端异常消息）。需要安装 Node.js 18+、Maven 3.8+、JDK 11。

### 前置条件检查

```bash
node --version    # 需要 18.x 或以上
npm --version
mvn --version     # 需要 3.8.x 或以上
java --version    # 需要 JDK 11 或以上
docker --version
docker compose version
```

如果缺少相关工具，在 Ubuntu/WSL2 中可以执行：

```bash
# 安装 Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# 安装 Maven 和 JDK 11
sudo apt-get install -y maven openjdk-11-jdk
```

### 第一步：拉取最新代码并进入仓库根目录

```bash
cd /path/to/CATIA-Copilot-PLM
git pull
```

### 第二步：构建前端镜像

```bash
cd docdoku-plm-front

# 安装 npm 依赖
npm install

# 安装 Bower 依赖（前端使用 Bower 管理部分库）
npx bower install --allow-root

# 构建（grunt build + docker build）
# 构建完成后会产生本地镜像 docdoku/docdoku-plm-front:<版本号>
./build.sh
```

> 构建完成后执行 `docker images | grep docdoku-plm-front` 确认镜像已生成。

### 第三步：构建后端镜像

```bash
cd ../docdoku-plm-server

# Maven 构建（跳过测试，加快速度）
mvn clean package -DskipTests

# 构建 Docker 镜像
docker build -f docker/Dockerfile -t docdoku/docdoku-plm-server:2.6.2-zh .
```

> ⚠️ 后端构建时间较长（10–20 分钟），请耐心等待。

### 第四步：更新 docker-compose.yml 使用本地镜像

打开 `docdoku-plm-docker/docker-compose.yml`，修改 `front` 和 `back` 的镜像名：

```yaml
  front:
    image: docdoku/docdoku-plm-front:2.6.2   # 保持不变，已在本地构建同名镜像

  back:
    image: docdoku/docdoku-plm-server:2.6.2-zh   # 改为带 -zh 后缀的本地镜像
```

（如果您在第二步的 `./build.sh` 中构建的前端镜像版本号与 `docker-compose.yml` 中一致，前端可不修改。）

### 第五步：重启相关容器

```bash
cd docdoku-plm-docker

# 重建前端和后端容器（保留数据卷，不删除数据）
docker compose up --force-recreate --no-deps -d front back
```

### 第六步：验证

```bash
# 查看容器状态
docker compose ps

# 查看后端启动日志（等待出现 "deployed successfully" 字样）
docker compose logs -f back
```

启动完成后访问 [http://localhost:8000](http://localhost:8000)，语言切换方式同方案 A。

---

## 常用运维命令

```bash
# 查看所有容器状态
docker compose ps

# 查看某个服务的日志（实时）
docker compose logs -f front
docker compose logs -f back

# 停止所有服务
docker compose down

# 停止所有服务并删除所有数据（慎用！会丢失所有数据）
docker compose rm --stop --force -v
docker volume rm docdoku-plm-server-volume
```

---

## 语言切换操作步骤（上线后）

1. 打开浏览器，访问系统首页
2. 登录账号
3. 点击右上角用户头像 → **Account（账户）**
4. 找到 **Language（语言）** 下拉框，选择 **中文**
5. 点击保存
6. **刷新页面**（Ctrl+F5 / Cmd+Shift+R）即可全程中文显示

> 注册新账号时，注册表单中也有 Language 字段，可以在注册时直接选择中文。
