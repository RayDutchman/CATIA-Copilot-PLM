WSL2 + Docker Engine（不安装 Docker Desktop）
📋 前置条件检查
确认你的 Windows 10 21H2 支持 WSL2：

CPU 需支持虚拟化（大多数现代 CPU 都支持）
在 BIOS 中启用虚拟化（Intel VT-x 或 AMD-V）
检查虚拟化是否开启：打开任务管理器 → 性能 → CPU，查看"虚拟化：已启用"。

# 第一步：启用 WSL2
以管理员身份打开 PowerShell，执行：

PowerShell
# 1. 启用 WSL 功能
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

# 2. 启用虚拟机平台功能
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
重启电脑，然后继续：

# 3. 下载并安装 WSL2 内核更新包
直接访问微软官方下载链接：

👉 https://aka.ms/wsl2kernel

点击下载 wsl_update_x64.msi，双击运行安装，一路"下一步"完成。

PowerShell
# 4. 设置 WSL2 为默认版本
wsl --set-default-version 2

PowerShell
# 第二步：安装 Ubuntu
wsl --install -d Ubuntu
或者直接在开始菜单中打开之前安装的 Ubuntu 应用，这次应该能正常启动并完成初始化。

# 第四步：设置用户名和密码
Ubuntu 启动后会提示设置：

Code
Enter new UNIX username: 你的用户名
New password: 你的密码（输入时不显示，正常）
设置完成后即可正常使用 WSL2 Ubuntu 终端。

验证是否成功
在 PowerShell 中运行：

PowerShell
wsl -l -v
看到类似以下输出说明成功：

Code
  NAME      STATE           VERSION
* Ubuntu    Running         2
VERSION 列显示 2 即表示 WSL2 正常工作，之后可以继续执行 ./start.sh 部署项目。

# 第五步：在 Ubuntu 中安装 Docker Engine
打开刚安装的 Ubuntu 终端，依次执行以下命令：

bash
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

# 5. 更新并安装 Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 6. 将当前用户加入 docker 组（避免每次都要 sudo）
sudo usermod -aG docker $USER
newgrp docker
第三步：启动 Docker 并验证
bash
# 启动 Docker 服务
sudo service docker start

# 验证安装
docker --version
docker compose version

# 运行测试容器
docker run hello-world
看到 Hello from Docker! 说明安装成功 ✅

# 第六步：运行本项目
在 Ubuntu 终端中，进入项目目录并启动：

bash
# 进入 Windows 文件系统中的项目目录
# Windows 的 C: 盘在 WSL2 中挂载为 /mnt/c/
cd "/mnt/c/Users/你的用户名/项目路径/CATIA-Copilot-PLM"

# 启动项目
docker compose up -d
🔧 让 Docker 随 WSL2 自动启动（可选）
每次打开 Ubuntu 都需要手动 sudo service docker start，可以配置自动启动：

bash
# 编辑 WSL 配置，让 Ubuntu 启动时自动启动 Docker
echo '[boot]
command = service docker start' | sudo tee /etc/wsl.conf
以后每次打开 WSL2 终端，Docker 就自动运行了。