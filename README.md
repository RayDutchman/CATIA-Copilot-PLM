# CATIA-Copilot-PLM

基于 [DocDoku PLM 2.6.2](https://github.com/docdoku/docdoku-plm) 的二次开发版本，面向 CATIA 协同设计场景，增加中文支持并修复多处 Bug。

> **注意**：预构建的 DockerHub 镜像不包含本项目的修改，前端和后端均须从源码本地构建。

---

## 前置依赖

| 工具 | 版本要求 | 说明 |
|------|---------|------|
| Docker Engine | 24+ | 含 `docker compose`（Compose v2 插件） |
| JDK | 11 | 后端构建（推荐 Eclipse Temurin 11） |
| Maven | 3.6+ | 后端构建 |
| Node.js | 14.x | 前端构建（v16+ 与 grunt 插件不兼容） |

> 在任意 Linux 发行版或 Windows WSL2 下均可部署。如果是 Windows 环境，请参考 [docs/setup/deployment-wsl2-docker.md](docs/setup/deployment-wsl2-docker.md) 完成 WSL2 和 Docker 的初始配置。

---

## 首次部署流程

### 1. 克隆仓库

```bash
git clone <repo-url>
cd CATIA-Copilot-PLM
```

### 2. 构建后端基础镜像（仅首次，或清除 Docker 缓存后）

```bash
bash scripts/build-base-image.sh
```

这一步构建私有的 Payara 基础镜像（`docdoku/docdoku-plm-server-base:2.6.2`），包含 LibreOffice 等依赖，首次约需 10-20 分钟（取决于网速）。后续有缓存后可跳过。

### 3. 构建后端镜像

```bash
cd docdoku-plm-server
mvn clean install -DskipTests
docker build --build-arg VERSION=2.6.2 -f docker/Dockerfile -t docdoku/docdoku-plm-server:2.6.2 .
cd ..
```

首次 Maven 构建约需 5-15 分钟。

### 4. 构建前端镜像

需要 Node.js 14（推荐用 [nvm](https://github.com/nvm-sh/nvm) 管理版本）：

```bash
cd docdoku-plm-front
nvm use 14   # 或 node 14 的其他切换方式
npm install
npm run build
docker build -f docker/Dockerfile -t docdoku/docdoku-plm-front:2.6.2 .
cd ..
```

### 5. 构建转换服务镜像

转换服务将 STEP 文件转换为 GLB 格式供 3D 预览使用。仓库内已预置所有 Python wheels（离线安装，无需网络访问 PyPI）：

```bash
cd docdoku-plm-conversion-service
mvn package -DskipTests
docker build -f Dockerfile.jvm -t docdoku/docdoku-plm-conversion-service:2.6.2 .
cd ..
```

### 6. 启动所有服务

```bash
cd docdoku-plm-docker
bash start.sh
```

`start.sh` 会自动创建数据目录、生成密钥库，然后启动全部容器。后端冷启动约需 1-3 分钟。

### 7. 验证

访问 `http://localhost:8000`，默认管理员账号：`admin` / `changeit`。

---

## 服务端口

| 端口 | 服务 |
|------|------|
| 8000 | 前端 Web 界面（主入口） |
| 8001 | 后端 REST API |
| 8002 | Kibana（Elasticsearch 可视化） |
| 8003 | MailHog（邮件调试） |
| 8004 | Adminer（数据库管理） |
| 9000 | HTTPS 反向代理 |

---

## 日常运维命令

```bash
# 查看容器状态
docker ps

# 后续启动（不需要重新初始化）
cd docdoku-plm-docker && docker compose up -d

# 查看后端日志
cd docdoku-plm-docker && docker compose logs -f back

# 重启所有服务
cd docdoku-plm-docker && docker compose restart
```

构建脚本在 `scripts/` 目录下，修改源码后使用对应脚本重建：

| 脚本 | 用途 |
|------|------|
| `scripts/build-base-image.sh` | 构建 Payara 基础镜像（仅首次） |
| `scripts/build-backend-full.sh` | 完整重建后端 |
| `scripts/rebuild-front.sh` | 完整重建前端 |
| `scripts/rebuild-conversion-service.sh` | 重建转换服务 |

---

## 文档索引

```
docs/
├── setup/
│   ├── deployment-wsl2-docker.md   # WSL2 + Docker 完整部署指南
│   └── linux-ops-guide.md          # Linux 基础与日常运维
├── architecture/
│   ├── data-management.md          # 数据卷与容器交互架构
│   ├── 3d-visualization.md         # 3D 可视化与 CAD 转换机制
│   └── assembly-position.md        # 装配体位置信息机制
├── reference/
│   ├── rest-api.md                 # REST API 参考
│   ├── auth-and-accounts.md        # 认证与账号管理
│   └── user-manual.md              # 用户使用手册
└── issues/
    └── known-issues.md             # 已知问题与 Bug 追踪
```

---

## 当前开发状态

- **当前分支**：`fix/file-upload-npe-and-encoding`
- **主要分支**：`main`、`feat/vue3-frontend-modernization`

### 已完成修复
- 中文界面支持（前后端）
- 多处 NPE 修复（JWT、BasicHeader、ProductManager 等，详见 [known-issues.md](docs/issues/known-issues.md)）
- CAD 文件上传格式校验（前端 + 后端白名单）
- 文件名含特殊字符/中文时的 URI 编码问题
- 前端账号表单校验

### 已知限制
- CATIA 原生格式（`.CATPart`、`.CATProduct`、`.3dxml`）不支持转换，需在 CATIA 中预先导出为 STEP/STL

---

## AI 接管说明

本项目由亿航OS AI 助理（小亿）通过 SSH 远程操作 WSL Ubuntu 进行开发维护。

- WSL 环境保持不变，AI 通过 `wsl -d Ubuntu -- bash -lc '...'` 执行所有命令
- AI 可执行：git 操作、代码编辑、Maven/npm 构建、Docker 容器管理
- 项目上下文已存入 AI 长期记忆，新会话可直接接手

---

## 许可证

AGPL version 3
