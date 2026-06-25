# DocDokuPLM 项目交接文档

## 项目概述

**DocDokuPLM** 是一个开源的产品生命周期管理（PLM）系统，支持零件/装配体版本管理、3D 可视化、BOM 管理、工作流审批等功能。

- **技术栈**：Java EE 8 + Payara 5（后端），Bootstrap 2 + Backbone.js + Three.js（前端）
- **部署方式**：Docker Compose（PostgreSQL + Payara + 转换服务 + Nginx）
- **项目路径**：`/home/chenweibo/CATIA-Copilot-PLM`

---

## 快速启动

### 启动 Docker 环境

```bash
cd /home/chenweibo/CATIA-Copilot-PLM/docdoku-plm-docker
docker compose up -d
```

### 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 | http://localhost:8000 | 主 UI 入口 |
| 后端 API | http://localhost:8001/docdoku-plm-server-rest/api | REST API 基础路径 |
| SSL Proxy | https://localhost:9000 | HTTPS 访问（自签名证书） |

### 测试账号

| 用户名 | 密码 | 角色 | 说明 |
|--------|------|------|------|
| `admin` | `password` | 管理员 | 无 regular_user 角色，无法访问工作空间业务接口 |
| `testuser` | `testpass123` | 普通用户 | 已加入 `Workspace_0` |
| `test1` | `password` | 普通用户 | `Workspace_1` 管理员 |

---

## 核心概念

### 版本与迭代体系

| 术语 | 代码/DB | UI | 说明 |
|------|---------|-----|------|
| **Version** | `revision` | `version` | 字母序（A/B/C...），对应正式变更（ECO） |
| **Iteration** | `iteration` | `iteration` | 数字序（1/2/3...），同一 version 内的草稿迭代 |

- **Checkout**：创建新 iteration（如 A-1 → A-2），允许编辑
- **Checkin**：冻结当前 iteration，不可再修改
- **版本升级**：`createPartRevision`（A → B），物理复制附件到新 version 路径

### 产品配置（ConfigSpec）

| 类型 | 说明 |
|------|------|
| `latest` | 动态取每个零件各自最新已 checkin 的 iteration |
| `ProductBaseline` | 静态快照，精确冻结所有零件的 (partNumber, version, iteration) 组合 |

### 装配体与零件

- **装配体（Assembly）**：有子零件引用（`components` 非空）的零件
- **叶子零件（Leaf Part）**：无子零件的零件
- **本质**：装配体和叶子零件是同一个实体类（`PartMaster`），无 `assembly` 字段，通过 `isAssembly()` 动态判断

---

## 3D 可视化机制

### 转换流程

1. 上传原生 CAD 文件（STP/STEP/OBJ 等）到 `nativecad` 附件
2. 后端（`ConverterBean`）创建 Conversion 记录（`pending=true`），发送 Kafka 消息到 topic `CONVERT`
3. conversion 服务消费 Kafka，调用内置转换工具将 STEP 转换为 `.glb`（GLB 格式，不是 OBJ）
4. conversion 服务完成后 PUT 回调后端 `/api/.../conversion`
5. 后端 `handleConversionResultCallback` 将 `.glb` 写入 vault，更新 DB（`pending=false, succeed=true`）
6. 前端加载 `.glb` 文件，使用 Three.js 渲染（WebGL）

> 注意：Decimation（减面优化）步骤一直失败（`code=1 read error`），这是已知问题，**不影响 GLB 文件生成**。
> 不含实体几何的 STEP（如运动学约束件）会报 `no geometry generated`，后端已处理为 `succeed=true` 跳过，前端不会显示错误图标。

### 转换成功的必要条件

- 文件格式在白名单内（obj/stl/stp/step/igs/iges/ifc/dae 等）
- conversion 服务和 Kafka 正常运行
- ~~零件必须处于 Checkout 状态~~（已通过 `updateUsageLinksInConvertedIteration` 绕过此限制）

### 3D 查看器入口

| 入口 | 说明 |
|------|------|
| **入口 A：产品结构查看器** | 加载整棵装配树，递归合成变换矩阵，渲染所有叶子零件 |
| **入口 B：零件详情 CAD 预览** | 只渲染该零件自身的 `.glb`，不包含子零件 |
| **入口 C：iFrame 嵌入** | 生成独立 URL，可嵌入外部页面 |

### 坐标单位

| 字段 | 单位 |
|------|------|
| `.glb` 顶点坐标 | **毫米（mm）** |
| `tx / ty / tz` | **毫米（mm）** |
| `rx / ry / rz` | **弧度（rad）** |

---

## 附件存储机制

### 存储路径

```
{vault}/workspaces/{ws}/parts/{partNumber}/{version}/{iteration}/
  ├── nativecad/{fileName}      # 原生 CAD 文件
  ├── attachedfiles/{fileName}  # 普通附件
  └── {iteration}/              # 转换生成的 .obj/.mtl
```

### 关键特性

- **迭代间回溯**：Checkout 时只创建新 DB 记录，不复制物理文件；读取时 `BinaryStorageManagerBean` 自动回溯 `getPrevious()` 找物理文件
- **物理复制时机**：只在 `createPartRevision`（版本升级 A→B）时发生
- **同名文件覆盖**：同一 iteration 内上传同名文件会直接覆盖，不报错不重命名

---

## 构建与部署

### 后端构建

```bash
cd docdoku-plm-server
mvn clean install -DskipTests
```

生成的 WAR 包位于 `docdoku-plm-server-rest/target/docdoku-plm-server-rest.war`。

### 前端构建

```bash
cd docdoku-plm-front
npm install
npx grunt build
```

生成的静态文件位于 `dist/` 目录。

### 重建 Docker 镜像

**前端**：
```bash
docker build -t docdoku/docdoku-plm-front:2.6.2 \
  -f docdoku-plm-front/docker/Dockerfile \
  docdoku-plm-front
```

**后端**：
```bash
docker build -t docdoku/docdoku-plm-server:2.6.2 \
  --build-arg VERSION=2.6.2 \
  -f docdoku-plm-server/docker/Dockerfile \
  docdoku-plm-server
```

**转换服务**：
```bash
cd docdoku-plm-conversion-service/conversion-service
mvn clean package -DskipTests
docker build -t docdoku/docdoku-plm-conversion-service:2.6.2 \
  -f docker/Dockerfile .
```

### 重启容器

```bash
cd docdoku-plm-docker
docker compose down
docker compose up -d
```

---

## 已知问题与修复

详见 `docs/issues/known-issues.md`，包含：

- **BUG-01 ~ BUG-15**：高危 NPE 全量修复（已完成）
- **BUG-09**：文件上传格式校验（前端 accept + 后端白名单，已修复）
- **BUG-10**：CATIA 原生文件转换不支持（需商业 CAD 库，暂搁置）
- **BUG-16 ~ BUG-40**：历史 commit 修复记录

---

## 核心 API

### 零件管理

| 接口 | 说明 |
|------|------|
| `POST /api/workspaces/{ws}/parts` | 创建零件（自动 checkout，iter=1） |
| `PUT /api/workspaces/{ws}/parts/{number}-{version}/checkin` | Checkin 零件 |
| `PUT /api/workspaces/{ws}/parts/{number}-{version}/checkout` | Checkout 零件 |
| `PUT /api/workspaces/{ws}/parts/{number}-{version}/iterations/{iter}` | 更新 BOM（写 `components` 数组） |

### 文件上传

| 接口 | 说明 |
|------|------|
| `PUT /api/files/{ws}/parts/{number}/{version}/{iter}/nativecad` | 上传原生 CAD 文件（触发转换） |
| `POST /api/files/{ws}/parts/{number}/{version}/{iter}/attachedfiles` | 上传普通附件 |

### 3D 可视化

| 接口 | 说明 |
|------|------|
| `GET /api/workspaces/{ws}/products/{ciId}/instances?configSpec=latest` | 获取装配树（含变换矩阵） |
| `GET /api/workspaces/{ws}/parts/{number}-{version}/iterations/{iter}/conversion` | 查询转换状态 |
| `PUT /api/workspaces/{ws}/parts/{number}-{version}/iterations/{iter}/conversion` | 重试转换 |

---

## 数据库

### 连接信息

| 参数 | 值 |
|------|-----|
| 容器名 | `docdoku-plm-docker-db-1` |
| 主机 | `localhost:5432` |
| 数据库 | `docdokuplm` |
| 用户名 | `changeit` |
| 密码 | `changeit` |

### 关键表

| 表名 | 说明 |
|------|------|
| `partmaster` | 零件主记录（partNumber + workspace） |
| `partrevision` | 零件版本（A/B/C...） |
| `partiteration` | 零件迭代（1/2/3...） |
| `binaryresource` | 附件元数据（含 `fullName` 路径） |
| `partiteration_geometry` | 3D 几何文件关联（`geometryFileURI`） |
| `conversion` | 转换任务状态 |
| `cadinstance` | 装配体实例位置（tx/ty/tz/rx/ry/rz） |
| `baselinedpart` | Baseline 快照（冻结的零件版本） |

---

## 文档索引

| 文档 | 路径 | 说明 |
|------|------|------|
| **用户手册** | `docs/reference/user-manual.md` | 完整功能使用指南 |
| **REST API 笔记** | `docs/reference/rest-api.md` | API 分析与装配体上传流程 |
| **3D 可视化机制** | `docs/architecture/3d-visualization.md` | 转换流程、checkout 约束、单位分析 |
| **装配体位置机制** | `docs/architecture/assembly-position.md` | CADInstance 数据模型、矩阵合成 |
| **数据管理机制** | `docs/architecture/data-management.md` | 版本/迭代/附件/存储回溯机制 |
| **已知问题** | `docs/issues/known-issues.md` | BUG 记录与修复状态 |
| **认证与账号** | `docs/reference/auth-and-accounts.md` | JWT/Basic Auth 配置 |
| **部署指南** | `docs/setup/deployment-wsl2-docker.md` | WSL2 + Docker 部署步骤 |

---

## 关键源码位置

### 后端

| 文件 | 说明 |
|------|------|
| `docdoku-plm-server-rest/.../file/PartBinaryResource.java` | 文件上传接口（含格式白名单） |
| `docdoku-plm-server-ejb/.../ConverterBean.java` | 转换任务触发与回调（含 checkout 检查） |
| `docdoku-plm-server-ejb/.../ProductManagerBean.java` | 零件/装配体核心业务逻辑 |
| `docdoku-plm-server-ejb/.../BinaryStorageManagerBean.java` | 存储层封装（含回溯机制） |
| `docdoku-plm-server-rest/.../util/InstanceBodyWriterTools.java` | 装配体矩阵递归合成 |

### 前端

| 文件 | 说明 |
|------|------|
| `docdoku-plm-front/app/product-structure/js/dmu/InstancesManager.js` | 3D 场景管理（矩阵应用） |
| `docdoku-plm-front/app/parts/js/views/cad-file-view.js` | 零件详情 CAD 预览 |
| `docdoku-plm-front/app/parts/js/views/part-revision.js` | 零件详情页逻辑 |
| `docdoku-plm-front/app/js/common-objects/views/file/file_list.js` | 文件上传 UI（含格式校验） |

### 转换服务

| 文件 | 说明 |
|------|------|
| `docdoku-plm-conversion-service/conversion-service/.../GeometryParser.java` | OBJ 文件解析（bounding box 计算） |
| `docdoku-plm-conversion-service/conversion-service/.../StepFileConverterImpl.java` | STEP 转 OBJ（调用 FreeCAD） |
| `docdoku-plm-conversion-service/conversion-service/.../convert_step_obj.py` | FreeCAD Python 脚本 |

---

## 开发环境

### 必需工具

- **Java**：JDK 11+
- **Maven**：3.6+
- **Node.js**：14+ (前端构建)
- **Docker**：20.10+ (部署)
- **PostgreSQL 客户端**：psql / DBeaver（可选，用于数据库调试）

### IDE 推荐

- **后端**：IntelliJ IDEA / Eclipse
- **前端**：VS Code
- **数据库**：DBeaver

---

## 常见操作

### 查看日志

```bash
# 后端日志
docker logs -f docdoku-plm-docker-server-1

# 转换服务日志
docker logs -f docdoku-plm-docker-conversion-1

# 数据库日志
docker logs -f docdoku-plm-docker-db-1
```

### 进入容器

```bash
# 后端容器
docker exec -it docdoku-plm-docker-server-1 bash

# 数据库容器
docker exec -it docdoku-plm-docker-db-1 psql -U changeit -d docdokuplm
```

### 清理数据重新开始

```bash
cd docdoku-plm-docker
docker compose down -v  # -v 删除 volume（包括数据库数据）
docker compose up -d
```

---

## CATIA V5 原生格式转换（可行性研究）

> 对应已知问题 **BUG-10**，本节记录 2026-05-25 会话的深度技术调研结论。

### 问题背景

CATPart / CATProduct 是 Dassault Systèmes 的**专有封闭二进制格式**，当前转换服务（FreeCAD）完全无法处理。用户必须在 CATIA 中手动预导出为 STP 才能上传，体验极差。

### 为什么无法纯 Docker 化

| 障碍 | 说明 |
|------|------|
| 格式解析器封闭 | CATIA 读取 CATPart 的代码封装在私有 DLL 中，无法合法剥离或逆向 |
| License 锁定 | 相关库运行时验证 CATIA License Server（LUM），Docker 容器无法通过授权检查 |
| 平台限制 | CATIA V5 Automation API 仅支持 Windows（COM/OLE），无 Linux 版本 |
| 法律风险 | 逆向 Dassault 二进制文件违反 EULA |

开源替代（如 Open CASCADE）对 CATIA V5 格式的支持极为有限，无法作为生产级方案。

### 唯一实际可行方案：混合架构

```
┌────────────────────────────────────────────┐
│          Linux Docker 环境（现有）           │
│  Kafka → conversion-service                │
│           ↓ 识别到 .catpart/.catproduct     │
│           ↓ HTTP 委托请求                  │
└───────────────────┬────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────┐
│   Windows 宿主机（已安装 CATIA V5）         │
│   轻量级 Python HTTP 代理服务               │
│       ↓ win32com → CATIA V5 COM API        │
│       ↓ CATIA 打开文件 → 另存为 STP        │
│       ↓ 返回 STP 文件路径给 Docker 侧       │
└────────────────────────────────────────────┘
```

Docker 侧新增 `CatiaFileConverterImpl.java`（仿照 `StepFileConverterImpl`），对 `catpart`/`catproduct` 扩展名调用 Windows 代理，获得 STP 后交回现有 STP→OBJ 流程。

### 工作量估算

| 模块 | 内容 | 难度 | 估时 |
|------|------|------|------|
| Windows 代理服务 | Python HTTP server + win32com 调用 CATIA V5 | 中 | 1~2 天 |
| CATPart 导出逻辑 | 单零件 STP 导出 | 中 | 0.5 天 |
| CATProduct 复杂性 | 装配体含子引用，需递归处理子零件路径 | **高** | 1~2 天 |
| Docker 侧新增 Converter | `CatiaFileConverterImpl.java` | 低 | 0.5 天 |
| 文件传输机制 | Vault（Linux）↔ Windows 共享路径 | 中 | 0.5~1 天 |
| 错误处理 / 超时 | CATIA 崩溃、License 不可用、文件损坏 | 中 | 0.5 天 |
| 集成测试 | 端到端验证 | 中 | 0.5 天 |
| **合计** | | | **约 4.5~7 天** |

### 主要风险点

1. **CATProduct 子零件路径**：CATProduct 以绝对/相对路径引用子 CATPart，路径在代理服务机器上不存在时导出失败——实践中最常见的坑，需要预先规划文件同步策略。
2. **License 并发**：自动化调用占用一个 CATIA License seat，批量转换时可能产生并发冲突，需要串行队列或 License 池管理。
3. **CATIA 进程稳定性**：长时间 COM 自动化偶发进程卡死，需进程监控 + 强制重启机制。
4. **WSL mirrored 网络**：Windows 与 WSL 共享网络栈，文件共享路径需统一规划（`\\wsl$\` vs `/mnt/`）。

### 当前决策状态

**待定**。推进前需确认以下两个前提：
- [ ] 是否接受"Windows 宿主机常驻一个 Python 代理服务"这个架构约束？
- [ ] 是否需要处理 CATProduct（装配体）？仅 CATPart 复杂度低很多。

商业替代方案（如 CADExchanger，约 $3k+/年）可实现纯 Docker 化，但需额外采购授权。

---

## 下一步工作

1. **完成 CAD 预览文档更新**（`user-manual.md` 和 `3d-visualization.md`）
2. 为各语言包补充 `FILE_FORMAT_NOT_SUPPORTED` i18n key
3. 根据需要继续处理未修复 Bug（BUG-11 ~ BUG-15 中未修复条目）
4. 考虑实现装配体/零件过滤功能（前端或后端方案）
5. **决策：是否推进 CATIA V5 → STP 混合架构方案**（见上方可行性研究章节，需确认架构约束后再启动实现）

---

## 联系与支持

- **项目仓库**：https://github.com/docdoku/docdoku-plm
- **官方文档**：https://www.docdokuplm.com/
- **问题反馈**：GitHub Issues

---

**最后更新**：2026-05-25（新增 CATIA V5 原生格式转换可行性研究）
