# CATIA-Copilot-PLM

基于 [DocDoku PLM 2.6.2](https://github.com/docdoku/docdoku-plm) 的二次开发版本，面向 CATIA 协同设计场景，增加中文支持并修复多处 Bug。

> **注意**：预构建的 DockerHub 镜像不包含本项目的修改，前端和后端均须从源码本地构建。

---

## 前置依赖

| 工具 | 版本要求 | 说明 |
|------|---------|------|
| Docker Engine | 24+ | 含 `docker compose`（Compose v2 插件） |
| Node.js | 14.x | 前端构建（推荐通过 [nvm](https://github.com/nvm-sh/nvm) 安装：`nvm install 14`） |

> 在任意 Linux 发行版或 Windows WSL2 下均可部署。WSL2 配置参考 [docs/setup/deployment-wsl2-docker.md](docs/setup/deployment-wsl2-docker.md)。

---

## 首次部署

```bash
# 1. 克隆仓库
git clone https://github.com/RayDutchman/CATIA-Copilot-PLM.git
cd CATIA-Copilot-PLM

# 2. 构建所有镜像（约 5-10 分钟）
./setup.sh build

# 3. 启动服务
./setup.sh up
```

服务就绪后访问 `http://localhost:8000`，注册账号后执行提权命令即可：

```bash
# 将 <your-login> 替换为你注册的登录名
docker exec docdoku-plm-docker-db-1 psql -U changeit -d docdokuplm \
  -c "INSERT INTO usergroupmapping (login, groupname) VALUES ('<your-login>', 'admin') ON CONFLICT DO NOTHING;"
```

---

## 日常命令

| 命令 | 说明 |
|------|------|
| `./setup.sh up` | 启动服务 |
| `./setup.sh down` | 停止服务 |
| `./setup.sh status` | 查看容器状态 |
| `./setup.sh logs [服务名]` | 查看日志（默认 back-py） |
| `./setup.sh build` | 修改源码后重建所有镜像 |

**单独重建某个服务**（日常开发用）：

| 脚本 | 用途 |
|------|------|
| `scripts/rebuild-front.sh` | 只重建前端镜像 |
| `scripts/build-i18n.sh` | 只重建国际化模块 |

**数据迁移（跨机器）**：

```bash
# 旧机器导出
cd docdoku-plm-docker && bash migrate.sh export

# 新机器（git clone + ./setup.sh build 之后）
cd docdoku-plm-docker && bash migrate.sh import
```

---

## 服务端口

| 端口 | 服务 |
|------|------|
| 8000 | 前端 Web 界面（主入口，nginx → back-py） |
| 8005 | 对比端口（nginx → Payara，仅本地开发用） |
| 8003 | MailHog（邮件调试） |
| 8004 | Adminer（数据库管理） |

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
