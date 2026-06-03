# CATIA-Copilot-PLM

基于 [DocDoku PLM 2.6.2](https://github.com/docdoku/docdoku-plm) 的二次开发版本，面向 CATIA 协同设计场景，增加中文支持并修复多处 Bug。

> **注意**：预构建的 DockerHub 镜像不包含本项目的修改，前端和后端均须从源码本地构建。

---

## 快速开始

| 步骤 | 文档 |
|------|------|
| WSL2 + Docker 环境搭建 | [docs/setup/deployment-wsl2-docker.md](docs/setup/deployment-wsl2-docker.md) |
| Linux 基础 & 日常运维 | [docs/setup/linux-ops-guide.md](docs/setup/linux-ops-guide.md) |

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

## 常用命令

```bash
# 查看容器状态
docker ps

# 启动所有服务（首次）
cd docdoku-plm-docker && bash start.sh

# 后续启动
cd docdoku-plm-docker && docker compose up -d

# 查看后端日志
cd docdoku-plm-docker && docker compose logs -f back

# 重启所有服务
cd docdoku-plm-docker && docker compose restart

# 构建前端镜像
cd docdoku-plm-front
nvm use 14 && npm run build
docker build -f docker/Dockerfile -t docdoku/docdoku-plm-front:2.6.2 .

# 构建后端镜像
cd docdoku-plm-server
mvn clean install -DskipTests
docker build --build-arg VERSION=2.6.2 -f docker/Dockerfile -t docdoku/docdoku-plm-server:2.6.2 .
```

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
