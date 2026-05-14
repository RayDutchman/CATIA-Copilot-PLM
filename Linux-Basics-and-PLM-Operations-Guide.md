# Linux 新手入门 & PLM 运维操作指南

> **本指南适合人群**：从未接触过 Linux，已按照 [WSL2-Docker-Engine-Deployment-Guide.md](./WSL2-Docker-Engine-Deployment-Guide.md) 完成 WSL2 + Docker Engine 安装的用户。
>
> 本指南从打开终端开始，涵盖 Linux 基础命令、项目启动、日常运维和常见问题排查。

---

## 目录

1. [打开 WSL2 终端](#1-打开-wsl2-终端)
2. [Linux 终端基础操作](#2-linux-终端基础操作)
3. [导航到项目目录](#3-导航到项目目录)
4. [启动 PLM 系统（start.sh）](#4-启动-plm-系统startsh)
5. [验证服务运行状态](#5-验证服务运行状态)
6. [访问 Web 界面](#6-访问-web-界面)
7. [查看运行日志](#7-查看运行日志)
8. [停止与重启服务](#8-停止与重启服务)
9. [常见问题排查](#9-常见问题排查)
10. [完全重置（清空数据重新开始）](#10-完全重置清空数据重新开始)

---

## 1. 打开 WSL2 终端

有三种方式可以打开 Ubuntu 终端：

| 方式 | 操作 |
|------|------|
| 开始菜单 | 搜索 **Ubuntu**，点击打开 |
| Windows Terminal | 点击标签页旁边的 `+` → 选择 **Ubuntu** |
| 右键菜单 | 在 Windows 文件夹内右键 → **在 Linux 中打开** |

打开后你会看到类似这样的提示符，说明终端已就绪：

```
你的用户名@电脑名:~$
```

> `~` 表示当前在你的**主目录**（即 `/home/你的用户名`），`$` 表示可以输入命令。

---

## 2. Linux 终端基础操作

### 2.1 常用快捷键

| 快捷键 | 作用 |
|--------|------|
| `Tab` | **自动补全**路径或命令（强烈推荐，避免手动拼写错误） |
| `↑` / `↓` | 翻看历史命令，无需重复输入 |
| `Ctrl + C` | **中止**当前正在运行的命令 |
| `Ctrl + L` | 清屏（等同于 `clear` 命令） |
| `Ctrl + D` | 退出当前终端会话 |

### 2.2 常用命令速查

```bash
# 显示当前所在目录的完整路径
pwd

# 列出当前目录的文件和文件夹
ls

# 列出详细信息（含文件大小、权限、修改时间）
ls -l

# 进入指定目录
cd 目录名

# 返回上一级目录
cd ..

# 回到主目录（~）
cd ~

# 查看文件内容（小文件）
cat 文件名

# 逐页查看文件内容（大文件）；按 q 退出
less 文件名

# 查看文件末尾 50 行内容
tail -n 50 文件名

# 创建新目录
mkdir 目录名

# 删除文件（谨慎操作！）
rm 文件名

# 以管理员权限执行命令
sudo 命令
```

> **关于 `sudo`**：Linux 中修改系统设置需要管理员权限，在命令前加 `sudo` 并输入你的 Ubuntu 密码即可。密码输入时不会显示任何字符，这是正常现象，直接输完按回车即可。

### 2.3 路径规则

- `/` 是 Linux 的根目录（类似 Windows 的 `C:\`）
- Windows 的磁盘在 WSL2 中被挂载到 `/mnt/` 下：
  - `C:\` → `/mnt/c/`
  - `D:\` → `/mnt/d/`
- `~` 是当前用户的主目录，等同于 `/home/你的用户名`

---

## 3. 导航到项目目录

项目文件存放在 Windows 文件系统中，通过 `/mnt/` 路径访问。

假设你把项目克隆到了 `C:\Users\Ray\Projects\CATIA-Copilot-PLM`，则在 Ubuntu 终端中执行：

```bash
cd "/mnt/c/Users/Ray/Projects/CATIA-Copilot-PLM/docdoku-plm-docker"
```

> **提示**：路径中有空格时，整个路径需要用引号包裹。可以用 `Tab` 键自动补全，减少手动输入。

验证你已进入正确目录：

```bash
pwd
# 应显示：/mnt/c/Users/.../CATIA-Copilot-PLM/docdoku-plm-docker

ls
# 应显示：README.md  docker-compose.yml  env  proxy  start.sh
```

---

## 4. 启动 PLM 系统（start.sh）

在 `docdoku-plm-docker` 目录内执行启动脚本：

```bash
./start.sh
```

> **首次运行**时，脚本会自动完成以下工作：
> 1. 创建 `data` 数据目录（用于存储上传的文件）
> 2. 生成加密密钥库（Keystore）
> 3. 从 Docker Hub 拉取所有镜像（**需要几分钟，取决于网速**）
> 4. 启动全部容器

如果遇到权限错误，先赋予脚本执行权限：

```bash
chmod +x start.sh
./start.sh
```

看到类似下面的输出说明启动成功：

```
[+] Running 10/10
 ✔ Container docdoku-plm-docker-db-1          Started
 ✔ Container docdoku-plm-docker-es-1          Started
 ✔ Container docdoku-plm-docker-smtp-1        Started
 ✔ Container docdoku-plm-docker-front-1       Started
 ✔ Container docdoku-plm-docker-back-1        Started
 ...
```

> **注意**：容器启动不等于服务就绪。后端（`back`）服务通常需要 **1～3 分钟**才能完全初始化，请耐心等待后再访问浏览器。

---

## 5. 验证服务运行状态

```bash
docker compose ps
```

正常状态下，所有服务的 `STATUS` 列均应显示 `Up` 或 `running`：

```
NAME                                  STATUS
docdoku-plm-docker-adminer-1          Up
docdoku-plm-docker-back-1             Up
docdoku-plm-docker-conversion-1       Up
docdoku-plm-docker-db-1               Up
docdoku-plm-docker-es-1               Up
docdoku-plm-docker-front-1            Up
docdoku-plm-docker-kafka-1            Up
docdoku-plm-docker-kibana-1           Up
docdoku-plm-docker-smtp-1             Up
docdoku-plm-docker-ssl-proxy-1        Up
docdoku-plm-docker-zookeeper-1        Up
```

如果某个服务显示 `Exit` 或 `Restarting`，说明该服务启动失败，请参考[第 9 节](#9-常见问题排查)。

---

## 6. 访问 Web 界面

服务全部启动后，在 **Windows 浏览器**（如 Edge、Chrome）中打开以下地址：

| 地址 | 用途 |
|------|------|
| **http://localhost:8000** | 📦 PLM 主界面（日常使用入口） |
| http://localhost:8001 | 🔧 后端 API 接口 |
| http://localhost:8002 | 📊 Kibana（日志可视化，可选） |
| http://localhost:8003 | 📧 MailHog（邮件测试收件箱） |
| http://localhost:8004 | 🗄️ Adminer（数据库管理界面） |

### 首次登录 PLM

打开 http://localhost:8000 后，点击 **Sign up** 注册一个新账号，即可开始使用。

> **数据库连接信息**（用于 Adminer，http://localhost:8004）：
>
> | 字段 | 值 |
> |------|----|
> | 系统 | PostgreSQL |
> | 服务器 | `db` |
> | 用户名 | `changeit` |
> | 密码 | `changeit` |
> | 数据库 | `docdokuplm` |

---

## 7. 查看运行日志

当某个服务不正常时，查看日志是排查问题的首要手段。

```bash
# 实时跟踪后端日志（按 Ctrl+C 退出跟踪）
docker compose logs -f back

# 查看数据库日志
docker compose logs db

# 查看 Elasticsearch 日志
docker compose logs es

# 查看所有服务的最近 100 行日志
docker compose logs --tail=100
```

后端完全启动后，日志中会出现类似：

```
[back] INFO  Server startup in 45678 ms.
```

看到这行说明后端已就绪，可以正常使用。

---

## 8. 停止与重启服务

```bash
# 停止并移除所有容器（数据不会丢失）
docker compose down

# 再次启动所有服务（不需要重新运行 start.sh）
docker compose up -d

# 重启单个服务（例如只重启后端）
docker compose restart back

# 强制重建并重启单个服务
docker compose up -d --force-recreate --no-deps back
```

> **区别**：
> - `docker compose down` 只停止并删除容器，**数据卷（volumes）保留**，数据不会丢失。
> - 加上 `-v` 参数（`docker compose down -v`）才会同时删除数据卷，**慎用**。

---

## 9. 常见问题排查

### ❌ 问题：`./start.sh` 报错 `Permission denied`

```bash
# 赋予执行权限后重试
chmod +x start.sh
./start.sh
```

### ❌ 问题：`docker compose ps` 显示某服务 `Exit`

```bash
# 查看该服务的日志，找到报错原因
docker compose logs back   # 将 back 替换为实际出错的服务名
```

### ❌ 问题：浏览器打开 localhost:8000 显示无法连接

1. 等待 2～3 分钟，后端服务初始化较慢
2. 确认 Docker 服务正在运行：`sudo service docker status`
3. 确认前端容器状态正常：`docker compose ps front`

### ❌ 问题：`docker compose` 命令报 "cannot connect to Docker daemon"

```bash
# 启动 Docker 服务
sudo service docker start

# 验证 Docker 正常运行
docker info
```

### ❌ 问题：`es` 服务一直 `Restarting`

Elasticsearch 要求系统虚拟内存参数足够大，执行以下命令修复：

```bash
# 临时生效（重启 WSL2 后失效）
sudo sysctl -w vm.max_map_count=262144

# 永久生效
echo 'vm.max_map_count=262144' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

修复后重新启动 es 服务：

```bash
docker compose up -d es
```

### ❌ 问题：关闭 Windows 后再打开，服务没了

WSL2 关闭后容器会停止运行。重新进入终端后只需执行：

```bash
cd "/mnt/c/Users/你的用户名/项目路径/CATIA-Copilot-PLM/docdoku-plm-docker"
sudo service docker start   # 如果没有配置自动启动
docker compose up -d
```

---

## 10. 完全重置（清空数据重新开始）

> ⚠️ **警告**：以下操作会**永久删除所有数据**，包括数据库内容、上传的文件和容器。操作前请确认无需保留数据。

```bash
# 确保在 docdoku-plm-docker 目录内操作
cd "/mnt/c/Users/你的用户名/项目路径/CATIA-Copilot-PLM/docdoku-plm-docker"

# 1. 停止并删除所有容器和网络
docker compose rm --stop --force -v

# 2. 删除数据目录
rm -rf ./data

# 3. 删除密钥库文件
rm -f ./keystore

# 4. 删除 Docker 数据卷
docker volume rm docdoku-plm-server-volume

# 5. 重新运行启动脚本
./start.sh
```

重置完成后，系统将以全新状态启动，需要重新注册账号。

---

## 附录：常用命令汇总

```bash
# ── 日常启动 ──────────────────────────────────────────
sudo service docker start          # 启动 Docker（如未配置自动启动）
docker compose up -d               # 启动所有容器

# ── 状态查看 ──────────────────────────────────────────
docker compose ps                  # 查看所有容器状态
docker compose logs -f back        # 实时跟踪后端日志

# ── 停止操作 ──────────────────────────────────────────
docker compose down                # 停止所有容器（保留数据）
docker compose restart back        # 重启指定服务

# ── 故障修复 ──────────────────────────────────────────
sudo sysctl -w vm.max_map_count=262144   # 修复 Elasticsearch 启动失败
```
