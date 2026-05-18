# WSL2 + Docker Engine 部署指南

> 本指南适用于 **Windows 10 21H2 及以上版本**，无需安装 Docker Desktop，直接在 WSL2 内安装原生 Docker Engine。
>
> 本项目已对原始 DocDoku PLM 2.6.2 做了若干修改（去除西班牙语、增加中文支持、自动按浏览器语言显示界面等），预构建的 DockerHub 镜像**不包含**这些修改，因此前端和后端都需要从源码本地构建。**请务必按本指南操作**，而非使用上游 README。

---

## 📋 前置条件检查

在开始之前，确认以下条件已满足：

- CPU 支持虚拟化（Intel VT-x 或 AMD-V，现代 CPU 通常已支持）
- 在 BIOS 中已启用虚拟化选项
- 验证方法：打开**任务管理器** → **性能** → **CPU**，查看"虚拟化：已启用"

---

## 第一步：启用 WSL2

以**管理员身份**打开 PowerShell，依次执行以下命令：

```powershell
# 1. 启用 WSL 功能
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

# 2. 启用虚拟机平台功能
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```

执行完毕后，**重启电脑**，然后继续：

```powershell
# 3. 设置 WSL2 为默认版本
wsl --set-default-version 2
```

> **注意**：如果重启后提示缺少 WSL2 内核，请访问 https://aka.ms/wsl2kernel 下载并安装 `wsl_update_x64.msi`，然后再执行上面的第 3 步。

---

## 第二步：安装 Ubuntu

在 PowerShell 中执行：

```powershell
wsl --install -d Ubuntu
```

> 也可以在 Microsoft Store 中搜索 **Ubuntu** 并安装。安装完成后，从开始菜单打开 Ubuntu，等待初始化完成。

---

## 第三步：设置用户名和密码

Ubuntu 首次启动时会提示创建账户：

```
Enter new UNIX username: 你的用户名
New password: 你的密码（输入时不显示，属于正常现象）
```

设置完成后即可正常使用 WSL2 Ubuntu 终端。

### 验证 WSL2 是否正常工作

在 PowerShell 中运行：

```powershell
wsl -l -v
```

看到以下输出说明成功：

```
  NAME      STATE           VERSION
* Ubuntu    Running         2
```

`VERSION` 列显示 `2` 即表示 WSL2 正常工作 ✅

---

## 第四步：在 Ubuntu 中安装 Docker Engine

打开 Ubuntu 终端，依次执行以下命令：

```bash
# 1. 更新包索引
sudo apt-get update

# 2. 安装必要依赖
sudo apt-get install -y ca-certificates curl gnupg

# 3. 添加 Docker 官方 GPG 密钥
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# 4. 添加 Docker 软件源
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 5. 更新包索引并安装 Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 6. 将当前用户加入 docker 组（避免每次都需要 sudo）
sudo usermod -aG docker $USER
newgrp docker
```

---

## 第五步：启动 Docker 并验证

```bash
# 启动 Docker 服务
sudo service docker start

# 验证安装版本
docker --version
docker compose version

# 运行测试容器
docker run hello-world
```

看到 `Hello from Docker!` 输出说明安装成功 ✅

---

## 第六步：配置 DrvFs 挂载选项（Java 构建必须）

WSL2 默认挂载 Windows 磁盘（`/mnt/d/` 等）时不带 `metadata` 选项，导致 Java NIO 的文件操作（如 Maven `maven-resources-plugin` 复制资源文件）报 `FileSystemException: Operation not permitted`，即使 shell 的 `cp` 命令可以正常工作。

> **为什么第一次没遇到**：某些 WSL2 环境（如曾经安装过 Docker Desktop）会自动写入该配置。重装 Ubuntu 后的干净环境默认不带此选项。

在 Ubuntu 终端执行（**注意：需要手动输入最后一行的 `EOF` 并回车**）：

```bash
sudo tee -a /etc/wsl.conf << 'EOF'

[automount]
options = "metadata,umask=22,fmask=11"
EOF
```

然后在 **PowerShell** 中重启 WSL2 使配置生效：

```powershell
wsl --shutdown
```

重新打开 Ubuntu 终端，验证挂载参数已更新：

```bash
cat /proc/mounts | grep 'mnt/d'
# 输出中应包含 metadata
```

---

## 第七步（可选）：设置内核参数

如果后续启动时发现 `es`（Elasticsearch）容器反复退出，执行以下命令：

```bash
# 立即生效
sudo sysctl -w vm.max_map_count=262144

# 永久写入配置（重启 WSL 后仍有效）
echo 'vm.max_map_count=262144' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

> **背景**：Elasticsearch 要求 `vm.max_map_count` ≥ 262144。WSL2 通常会从 Windows 主机继承该值，但在某些环境（如重装 Ubuntu 后）可能低于要求，导致 `es` 容器启动即崩溃，进而引发后端不可用。

---

## 第八步：构建前端镜像

本项目对前端做了修改（自动按浏览器语言切换界面、移除西班牙语），这些改动存在于 JS 源码（各子应用的 `main.js`）中，**无法通过卷挂载绕过**，必须从源码构建前端镜像。

### 前置工具

前端构建依赖 Node.js 14（v16+ 与 grunt 插件不兼容）。

> **注意**：NodeSource 的 `setup_14.x` 脚本不支持 Ubuntu 25.04（resolute）及更新版本，请使用 **nvm** 安装：

```bash
# 安装 nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc

# 安装并激活 Node.js 14
nvm install 14
nvm use 14

# 验证
node --version   # 应显示 v14.x.x
npm --version    # 应显示 6.x.x
```

每次新开终端后，需要重新激活 Node.js 14（nvm 默认会读取 `~/.bashrc` 自动加载，但若未生效请手动执行）：

```bash
nvm use 14
```

### 8-1. 安装依赖

```bash
cd /mnt/d/CATIA-Copilot-Project/CATIA-Copilot-PLM/docdoku-plm-front

# --ignore-scripts 跳过 phantomjs 安装（phantomjs 只用于测试，构建不需要）
npm install --ignore-scripts
```

然后安装前端 bower 依赖（jQuery、AngularJS、Bootstrap 等浏览器端库）：

```bash
./node_modules/.bin/bower install --allow-root
```

> **注意**：bower 的安装目录由 `.bowerrc` 配置为 `app/bower_components/`（而非根目录的 `bower_components/`）。如果该目录已存在且有内容（Windows 文件系统上保留的），bower 会认为已安装完成并立即退出，属于正常现象。验证方法：
> ```bash
> ls app/bower_components | head -5
> ```
> 看到 `async`、`backbone`、`bootstrap` 等目录即表示依赖已就绪 ✅

### 8-2. 构建静态文件

> **快捷方式**：如果 `dist/` 目录已存在且内容完整（例如从之前成功的构建中保留），可直接跳到 **8-3** 构建 Docker 镜像，无需重新运行耗时的 grunt 构建。

```bash
# 仍在 docdoku-plm-front/ 目录下执行
npm run build
# 等价于 grunt build，输出到 dist/ 目录
```

### 8-3. 构建前端 Docker 镜像

```bash
docker build \
  -f docker/Dockerfile \
  -t docdoku/docdoku-plm-front:2.6.2 \
  .
```

> ⏱ 总计约 5–15 分钟（主要耗时在 `npm run build` 的 grunt 压缩/合并步骤）。

---

## 第九步：构建后端镜像

本项目对后端也做了修改（增加中文语言支持、修复多个 Bug），同样必须从源码构建。

### 前置工具

```bash
sudo apt-get update
sudo apt-get install -y maven openjdk-11-jdk

# 验证
java -version   # 应显示 openjdk 11
mvn -version    # 应显示 Apache Maven 3.x
```

### 9-0. 构建 Payara 基础镜像（首次，或清空 Docker 缓存后）

后端 Dockerfile 依赖私有基础镜像 `docdoku/docdoku-plm-server-base:2.6.2`，无法从 Docker Hub 拉取，需本地构建一次：

```bash
cd /mnt/d/CATIA-Copilot-Project/CATIA-Copilot-PLM/docdoku-plm-server

docker build \
  -f docker/payara/Dockerfile \
  -t docdoku/docdoku-plm-server-base:2.6.2 \
  docker/payara/
```

> ⏱ 首次约 5–20 分钟（需下载 Payara 镜像并安装 LibreOffice）。构建完成后无需重复执行。

### 9-1. Maven 构建后端

```bash
cd /mnt/d/CATIA-Copilot-Project/CATIA-Copilot-PLM/docdoku-plm-server

# 完整构建（跳过测试）—— 首次约 5–15 分钟
mvn clean install -DskipTests
```

### 9-2. 构建后端 Docker 镜像

```bash
# 仍在 docdoku-plm-server/ 目录下执行
docker build \
  --build-arg VERSION=2.6.2 \
  -f docker/Dockerfile \
  -t docdoku/docdoku-plm-server:2.6.2 \
  .
```

---

## 第十步：启动所有服务

```bash
cd /mnt/d/CATIA-Copilot-Project/CATIA-Copilot-PLM/docdoku-plm-docker
bash start.sh
```

`start.sh` 会自动完成初始化工作：创建 `data` 目录、创建 Docker 卷、生成密钥库（若不存在），最后启动全部容器。

> **首次部署**使用 `bash start.sh`；**后续重启**（无需重新初始化）只需：
> ```bash
> docker compose up -d
> ```

---

## 第十一步：等待后端就绪并验证

后端（Payara 应用服务器）冷启动需要 **1–3 分钟**。在此期间前端页面能加载，但所有 API 调用都会失败。

```bash
# 实时查看后端启动日志，等到出现 "Deployed" 字样再访问
docker compose logs -f back
```

启动完成后，在浏览器中访问：

```
http://localhost:8000
```

看到 DocDoku PLM 登录页面即表示部署成功 ✅

---

## 第十二步（可选）：加载示例数据

`docdoku-plm-sample-data` 是一个 Java 客户端工具，通过调用后端 REST API 自动创建用户、工作区、文档、零件、工作流等示例数据，便于快速体验系统功能。

> **前提**：第十一步中后端已完全启动（日志出现 `Deployed` 字样）。

### 12-1. 构建 sample-data 工具

`docdoku-plm-sample-data` 依赖 `docdoku-plm-api-java:2.6.2`，该库不在 Maven Central，需要先从本项目的 `docdoku-plm-api/` 目录本地构建安装。

> **注意**：`docdoku-plm-api-base` 和 `docdoku-plm-api-js` 两个子模块的 `pom.xml` 中，`exec-maven-plugin` 调用 `npm run build` 的 execution 已被设为 `<phase>none</phase>`（禁用），因此无需在系统中安装 npm 即可完成构建。这两个 npm 步骤仅用于生成 swagger-ui 文档，对 API JAR 本身无影响。

```bash
# 先安装 API 库到本地 Maven 仓库
cd /mnt/d/CATIA-Copilot-Project/CATIA-Copilot-PLM/docdoku-plm-api
mvn clean install -DskipTests

# 再构建 sample-data 工具
cd /mnt/d/CATIA-Copilot-Project/CATIA-Copilot-PLM/docdoku-plm-sample-data
mvn clean install
mvn dependency:copy-dependencies
```

### 12-2. 运行加载脚本

```bash
# 仍在 docdoku-plm-sample-data/ 目录下执行
# -u  登录名（会自动创建该账号）
# -p  密码
# -h  后端 API 地址（注意：需包含 context path，程序内部会自动追加 /api）
# -w  工作区名称（可选，不指定则自动生成）
java -classpath target/docdoku-plm-sample-data.jar:target/dependency/docdoku-api-java-2.5.4-SNAPSHOT.jar:target/dependency/* \
  com.docdoku.loaders.Main \
  -u admin \
  -p adminPass \
  -h http://localhost:8001/docdoku-plm-server-rest \
  -w demo
```

> **注意**：`-h` 参数必须包含 `/docdoku-plm-server-rest`，程序内部会自动在末尾追加 `/api`，最终调用 `http://localhost:8001/docdoku-plm-server-rest/api/...`。若只填 `http://localhost:8001` 会得到 404 Not Found 错误。

加载完成后，用 `-u` 和 `-p` 指定的账号登录 `http://localhost:8000`，即可看到示例工作区和数据。

### 端口映射一览

```
端口    服务
--------------------------
8000    docdoku-plm-front（主入口）
8001    docdoku-plm-server（后端 API）
8002    Kibana（Elasticsearch 可视化）
8003    MailHog（邮件调试）
8004    Adminer（数据库管理）
9000    SSL 反向代理（HTTPS，可选）
```

---

## 离线部署（迁移到无公网设备）

Docker 镜像存储在本机的 Docker 缓存中（WSL2 内部），无法直接复制文件夹。要在离线设备上部署，需要先将所有镜像导出为单个压缩包，拷贝后再导入。

### 第一步：在当前机器上导出所有镜像

在 WSL 终端执行，导出文件放到 `D:` 盘方便拷贝：

```bash
cd /mnt/d/CATIA-Copilot-Project/CATIA-Copilot-PLM

docker save \
  docdoku/docdoku-plm-front:2.6.2 \
  docdoku/docdoku-plm-server:2.6.2 \
  docdoku/docdoku-plm-server-base:2.6.2 \
  docdoku/docdoku-plm-conversion-service:2.6.2 \
  docker.elastic.co/elasticsearch/elasticsearch:6.6.1 \
  docker.elastic.co/kibana/kibana:6.6.1 \
  postgres:13.1-alpine \
  mailhog/mailhog:v1.0.1 \
  adminer:4.8.1 \
  confluentinc/cp-zookeeper:7.6.1 \
  confluentinc/cp-kafka:7.6.1 \
  nginx:1.19.1-alpine \
  -o docdoku-plm-images.tar
```

> ⏱ 所有镜像合计约 5–10 GB，导出需要几分钟。

### 第二步：拷贝以下内容到目标设备

| 文件/目录 | 说明 |
|-----------|------|
| `docdoku-plm-images.tar` | 刚才导出的镜像包 |
| `docdoku-plm-docker/` | 整个目录，含 `docker-compose.yml`、`env/`、`front/`、`proxy/`、`keystore` |

### 第三步：在目标设备上导入并启动

目标设备需先完成本指南的**第一步至第六步**（WSL2 + Docker Engine 安装 + DrvFs 配置），然后：

```bash
# 导入所有镜像（完全离线，无需联网）
docker load -i docdoku-plm-images.tar

# 进入 docker 目录启动
cd /mnt/d/.../docdoku-plm-docker   # 换成目标设备上的实际路径
docker compose up -d --force-recreate --remove-orphans
```

所有镜像已在本地，`docker compose up` 不会尝试从网络拉取任何内容。

---

## 🔧 可选：让 Docker 随 WSL2 自动启动

默认情况下，每次打开 Ubuntu 终端都需要手动执行 `sudo service docker start`。如果已启用 `systemd`（`/etc/wsl.conf` 中有 `[boot] systemd=true`），Docker 会随 systemd 自动启动，无需额外配置。

如果**没有启用 systemd**，可以在 `/etc/wsl.conf` 的 `[boot]` 段中加入启动命令：

```bash
# 注意：直接追加，不要覆盖整个文件（文件中已有其他配置）
sudo sed -i '/^\[boot\]/a command = service docker start' /etc/wsl.conf
```

或者手动编辑 `/etc/wsl.conf`，在 `[boot]` 段下加一行：

```ini
[boot]
systemd=true
command = service docker start
```

> **本项目的 `/etc/wsl.conf` 已启用 `systemd=true`**，Docker 会自动随 systemd 启动，无需上述操作。

---

## 常用运维命令

```bash
# 进入 docker 目录（以下命令均在此目录执行）
cd /mnt/d/CATIA-Copilot-Project/CATIA-Copilot-PLM/docdoku-plm-docker

# 查看所有容器状态
docker compose ps

# 查看实时日志
docker compose logs -f front
docker compose logs -f back
docker compose logs -f es

# 重启单个服务
docker compose up --force-recreate --no-deps -d front
docker compose up --force-recreate --no-deps -d back

# 停止所有服务（保留数据）
docker compose down

# 彻底清除所有容器和数据（⚠️ 不可恢复）
docker compose rm --stop --force -v
rm -rf ./data
docker volume rm docdoku-plm-server-volume
```

---

## 问题排查

| 现象 | 原因 | 解决方法 |
|------|------|----------|
| `es` 容器反复重启/退出 | `vm.max_map_count` 不足 | 执行**第七步** |
| 前端页面加载但所有操作报错 | `es` 崩溃导致后端不可用，或后端尚未就绪 | 先执行 `docker compose ps` 确认各容器状态；`es` 有问题则执行第七步 |
| `back` 容器启动失败，日志报 `keystore` 找不到 | `keystore` 文件不存在 | 在 `docdoku-plm-docker/` 目录执行 `bash start.sh` 完成初始化 |
| `docker compose up` 报 volume 错误 | `docdoku-plm-server-volume` 未创建 | 在 `docdoku-plm-docker/` 目录执行 `bash start.sh` 完成初始化 |
| 界面语言未自动跟随浏览器 / 显示旧版逻辑 | 前端镜像未重建，仍使用 DockerHub 原版 | 执行**第八步**从源码重建前端镜像 |
| Language 下拉框没有"中文"选项 | 后端镜像未重建，不含中文支持 | 执行**第九步**从源码重建后端镜像 |
| Maven 构建报 `Operation not permitted` | DrvFs 挂载缺少 `metadata` 选项 | 执行**第六步**配置挂载选项并重启 WSL2 |
| `docker build` 报 `pull access denied` for `docdoku-plm-server-base` | 该基础镜像是私有镜像，无法从 Docker Hub 拉取 | 执行**第九步 9-0** 本地构建基础镜像 |
| 访问 `localhost:8000` 显示空白或报 502 | 后端还在启动中 | 等待 1–3 分钟，执行 `docker compose logs -f back` 观察 |
| `npm run build` 报 `phantomjs` 安装失败 | phantomjs 在当前 Node 版本下安装脚本报错 | 使用 `npm install --ignore-scripts`（已在第八步说明） |
| Node.js 14 安装失败，提示发行版不受支持 | NodeSource 不支持 Ubuntu 25.04（resolute）及更新版本 | 改用 nvm 安装（见第八步前置工具） |
| `loadSample` 报连接拒绝或 404 | `-h` 缺少 context path，或后端尚未就绪 | 确认 `-h http://localhost:8001/docdoku-plm-server-rest`（不是 8000，也不是裸的 8001），并等后端日志出现 `Deployed` 再运行 |
| `loadSample` 报 409 Conflict | 该工作区已存在（脚本已做幂等处理，可忽略） | 正常现象，数据已加载，直接登录即可 |


---

## 界面语言设置

本项目支持中文（简体）、英语、法语、俄语界面。系统会根据浏览器语言自动选择显示语言；也可手动指定：

### 通过账户设置永久切换

1. 登录后点击右上角头像 → **Account（账号）**
2. 找到 **Language（语言）** 下拉框，选择 **中文（简体）**
3. 点击保存，刷新页面（`Ctrl+F5`）即生效

> 注册新账号时，注册表单中也有 Language 字段，可在注册时直接选择中文。

### 临时切换（浏览器控制台快捷方式）

无需修改账号设置，在浏览器开发者工具控制台（`F12` → **Console**）运行：

```javascript
localStorage.setItem('locale', 'zh');
location.reload();
```

> 此方法仅影响当前浏览器标签页，不保存到账户，关闭浏览器后恢复默认语言。
