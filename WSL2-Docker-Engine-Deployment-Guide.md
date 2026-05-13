# WSL2 + Docker Engine 部署指南

> 本指南适用于 **Windows 10 21H2 及以上版本**，无需安装 Docker Desktop，直接在 WSL2 内安装原生 Docker Engine。

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

> **注意**：如果重启后提示缺少 WSL2 内核，请访问 👉 https://aka.ms/wsl2kernel 下载并安装 `wsl_update_x64.msi`，然后再执行上面的第 3 步。

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

## 第六步：运行本项目

在 Ubuntu 终端中，进入项目目录并启动服务：

```bash
# Windows 磁盘在 WSL2 中的挂载路径：C: → /mnt/c/，D: → /mnt/d/，以此类推
cd "/mnt/c/Users/你的用户名/项目路径/CATIA-Copilot-PLM/docdoku-plm-docker"

# 启动所有服务
docker compose up -d
```

---

## 🔧 可选：让 Docker 随 WSL2 自动启动

默认情况下，每次打开 Ubuntu 终端都需要手动执行 `sudo service docker start`。可通过以下方式配置开机自启：

```bash
# 配置 WSL2 启动时自动运行 Docker 服务
echo '[boot]
command = service docker start' | sudo tee /etc/wsl.conf
```

配置生效后，每次打开 WSL2 终端，Docker 将自动在后台启动，无需手动干预。
