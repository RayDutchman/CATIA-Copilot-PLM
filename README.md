# DocDoku PLM — 本地化部署版

本仓库基于 [DocDoku PLM 2.6.2](https://github.com/docdoku/docdoku-plm) Fork 维护，在原版基础上做了以下改动：

- 增加**中文（简体）**界面支持，可通过账户设置切换语言
- 移除西班牙语支持
- 修复多处 Java 11 编译兼容性问题（JAXB、CORBA、pdfbox2-layout 依赖）
- 修复 PostgreSQL volume 挂载路径错误（原版写成了 MySQL 路径）
- 修复 nginx 缺少 `charset utf-8` 导致中文 NLS 文件乱码
- 修复 nginx 缺少 `try_files` 导致刷新页面 404

预构建的 DockerHub 镜像**不包含以上修改**，因此前后端均需从本仓库源码本地构建。

---

## 快速开始

参见 **[WSL2-Docker-Engine-Deployment-Guide.md](./WSL2-Docker-Engine-Deployment-Guide.md)**，内含从零开始的完整部署步骤，包括：

- WSL2 + Docker Engine 安装
- 前端镜像本地构建（Grunt + Docker）
- 后端镜像本地构建（Maven + Docker）
- 服务启动与验证
- 示例数据加载

---

## 主要功能

- **文档管理**：版本控制、工作流、模板、文档链接
- **产品结构**：零件树搜索与过滤
- **产品配置**：管理有效性、替代件与代换件
- **物料清单（BOM）**：列出产品原材料
- **流程管理**：定义工作流与任务
- **变更管理**：追踪设计修改
- **数据可视化**：浏览器内 WebGL 三维浏览、文档预览（Word、PDF、CAD）

---

## 端口一览

| 端口 | 服务 |
|------|------|
| 8000 | 前端 Web 界面（主入口） |
| 8001 | 后端 REST API |
| 8002 | Kibana（Elasticsearch 可视化） |
| 8003 | MailHog（邮件调试） |
| 8004 | Adminer（数据库管理） |
| 9000 | HTTPS 反向代理（可选） |

---

## 许可证

AGPL version 3
