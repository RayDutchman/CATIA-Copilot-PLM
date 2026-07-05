# Payara → FastAPI 完整迁移路线图

> **权威文档**：本文件是迁移路线图的唯一事实来源。取代散落在各 plan 文档和对话中的描述。每次规划新阶段前先读本文件。
> **最后更新**：2026-07-06（3轮全量审计清零 / 文件映射方法论 / Router 22→32 / Service 改名 / 142 passed）

---

## 决策与策略

**决策**：完整替换 Payara Java 后端（37 个 Resource 文件，145 张表，200+ 端点），保留 Backbone.js 前端和现有 PostgreSQL 数据库。

**策略**：分阶段逐步迁移，Nginx 双后端并行路由。**每阶段必须通过行为对齐验收后**才把对应路径切到 FastAPI，Payara 同步退出对应模块。

**关键约束**：
- API 路径前缀 `/docdoku-plm-server-rest/api` 完全不变
- JWT 与 Payara 共享同一个 `JWT_KEY`，两边颁发的 token 互认
- 数据库不改 schema，直接读写现有 145 张表
- 每阶段独立可测试、可回滚

---

## ⚠️ 执行教训（来自 P0/P1a/对齐审计，塑造了下方工作流）

1. **"端点能跑"≠"阶段完成"**。P1a 曾在 CRUD 端点自测通过后就切 Nginx，前端立刻坏：`geometryFileURI` 为 null、`UserDTO` 缺 name/email/language、datetime 格式不符、删除报 500 而非本地化消息。这些用"端点返回 200"测不出，只有与 Payara 对拍才发现。→ **每阶段必须有行为对齐门禁，在切 Nginx 之前。**

2. **i18n + 异常基础设施是全局共享地基**（P0 原计划没有，对齐审计批次 0 补建）。所有后续阶段必须复用，禁止硬编码错误消息。

3. **阶段之间并非干净独立——存在跨模块外键约束**。如 deletePartRevision 需检查 ProductConfiguration(P3)/ProductBaseline(P3)/ChangeItem(P4)，notifications 需 ModificationNotification(P5)。→ **打桩+TODO，等属主模块落地补齐，记入"对齐债务"表。**

4. **Payara 对拍脚本是可复用验收工具**（`scripts/compare_with_payara.py`），每阶段泛化使用。

5. **验收靠前端实测**（用户只测前端不看代码）。每阶段交付必须附"前端该测什么+预期行为"清单。

---

## 标准每阶段工作流（强制）

每个阶段（P1b 及以后）必须按此顺序执行：

1. **ORM 建模** — 含本模块表 + 跨模块只读依赖表的最小建模
2. **端点实现** — 抛 `ApplicationException` + i18n key，**禁止硬编码消息**
3. **行为对齐审计** — 逐方法对照 Payara：业务校验点 / i18n key / DTO 字段，产出对齐矩阵
4. **Payara 对拍** — `compare_with_payara.py` 关键操作无 diff（datetime 精度等已知差异除外）
5. **前端实测清单** — 列出该测哪些前端操作 + 预期行为，交用户验收
6. **切 Nginx 路由** — 仅在 1-5 全部通过后执行
7. **更新文档** — REMINDERS（对齐债务）+ CHANGELOG + 本路线图状态

---

## 跨阶段共享基础设施（P0 + 对齐审计批次 0 已建）

后续所有阶段直接复用，不重复造：

| 组件 | 路径 | 用途 |
|------|------|------|
| FastAPI 骨架 | `app/main.py` | 应用入口、路由注册、中间件 |
| JWT 认证 | `app/core/security.py`、`deps.py` | 与 Payara 共享 JWT_KEY，MD5 密码 |
| DB 连接 | `app/core/database.py` | SQLAlchemy，读写现有 145 张表 |
| vault 服务 | `app/services/vault.py` | CAD/GLB 文件路径 |
| Kafka 生产者 | `app/services/kafka_producer.py` | 触发 CAD 转换（topic CONVERT） |
| **i18n 加载器** | `app/core/i18n.py` | 复用 Java `LocalStrings_{en,fr,zh,ru}.properties` |
| **异常体系** | `app/core/exceptions.py` | `ApplicationException` + 业务子类 |
| **异常 handler** | `app/core/exception_handlers.py` | 异常→HTTP 状态码 + i18n 翻译 |
| **语言中间件** | `app/main.py` | 从 JWT 解析 Account.language 注入 request.state |
| **对拍脚本** | `scripts/compare_with_payara.py` | 与 Payara 响应字段级 diff |

**i18n/异常使用规范（强制）**：service 层抛 `raise NotAllowedException("NotAllowedException37")`，与 Java `throw new NotAllowedException("NotAllowedException37")` 一一对应。handler 按用户语言翻译。异常→状态码映射：AccessRight/NotAllowed/EntityConstraint→403，*NotFound→404，*AlreadyExists→409，Creation/其他→500。

---

## 阶段总览

| 子项目 | 内容 | 状态 | 计划文档 |
|--------|------|------|----------|
| **P0** | 基础设施（FastAPI 骨架、JWT、DB、vault、Kafka） | ✅ 完成 | `plans/2026-07-04-fastapi-migration-p0-infrastructure.md` |
| **P1a-core** | 零件核心 CRUD（ORM + 14 端点 + 签出签入 + BOM 更新） | ✅ 完成 | `plans/2026-07-04-fastapi-migration-p1a-parts-core.md` |
| **P1a-align** | 零件行为对齐（i18n 基础设施 + 7 方法错误消息 + DTO 字段） | ✅ 完成 | `plans/2026-07-04-payara-fastapi-parts-alignment.md` |
| **P1b** | 零件文件（nativecad 上传下载 + 附件 + 转换回调 + release/obsolete/tags + 搜索） | ✅ 完成 | `plans/2026-07-04-p1b-parts-files.md` |
| **P2** | 文档与文件夹（Documents/Folders/Tags/文档模板） | ✅ 完成 | — |
| **P3** | 产品结构（Products/ConfigurationItems/Baselines/ProductInstances/3D 装配树） | ✅ 完成 | — |
| **P4** | 变更管理（ChangeIssues/ChangeRequests/ChangeOrders/Milestones） | ✅ 完成 | — |
| **P5** | 工作流与权限（Workflow/WorkflowModel/Tasks/ACL/角色/用户组/Webhook/通知） | ✅ 完成 | — |

### 当前 Nginx 路由

```
/docdoku-plm-server-rest/api/auth/                         → FastAPI back-py:8000  （P0 已切）
/docdoku-plm-server-rest/api/workspaces/{ws}/parts...      → FastAPI back-py:8000  （P1a 已切）
/docdoku-plm-server-rest/api/files/{ws}/parts...           → FastAPI back-py:8000  （P1b 已切）
/docdoku-plm-server-rest/api/workspaces/{ws}/documents...  → FastAPI back-py:8000  （P2 已切）
/docdoku-plm-server-rest/api/workspaces/{ws}/folders...    → FastAPI back-py:8000  （P2 已切）
/docdoku-plm-server-rest/api/workspaces/{ws}/document-templates... → FastAPI back-py:8000  （P2 已切）
/docdoku-plm-server-rest/api/files/{ws}/documents...       → FastAPI back-py:8000  （P2 已切）
/docdoku-plm-server-rest/api/workspaces/{ws}/products...  → FastAPI back-py:8000  （P3 已切）
/docdoku-plm-server-rest/api/files/{ws}/products...       → FastAPI back-py:8000  （P3 已切）
/docdoku-plm-server-rest/api/workspaces/{ws}/changes...   → FastAPI back-py:8000  （P4 已切）
/docdoku-plm-server-rest/api/workspaces/{ws}/(users|groups|memberships|roles|workflow-models|workflow-instances|workspace-workflows|tasks|notifications|webhooks|user-group)... → FastAPI back-py:8000  （P5 已切）
/docdoku-plm-server-rest/api/workspaces/{ws}/(add-user|admin|user-access|...) → FastAPI back-py:8000  （P5 已切）
/docdoku-plm-server-rest/api/accounts...                   → FastAPI back-py:8000  （P5 已切）
/docdoku-plm-server-rest/api/workspaces(...)?...             → FastAPI back-py:8000  （补充：工作区 CRUD）
/docdoku-plm-server-rest/api/(admin|organizations|languages|timezones|platform|shared)... → FastAPI back-py:8000  （补充：Admin/Orgs/Misc/Shared）
其余全部                                                     → Payara back:8080
```

---

## 对齐债务追踪

跨模块约束/字段因属主模块未迁移而暂时打桩，等属主阶段落地时补齐：

| 债务 | 位置 | 属主阶段 | 说明 |
|------|------|----------|------|
| ~~deletePartRevision: 配置项根零件检查~~ | ~~P3~~ | ✅ 已补齐 | `EntityConstraintException1` — P3 落地后已实现 |
| ~~deletePartRevision: 基线检查~~ | ~~P3~~ | ✅ 已补齐 | `EntityConstraintException5` — P3 落地后已实现 |
| ~~deletePartRevision: 替代品检查~~ | ~~P3~~ | ✅ 已补齐 | `EntityConstraintException22` — P3 落地后已实现 |
| ~~deletePartRevision: 变更项检查~~ | ~~P4~~ | ✅ 已补齐 | `EntityConstraintException21` — P4 落地后已实现 |
| ~~PartRevisionDTO.notifications 字段~~ | ~~P5~~ | ✅ 已补齐 | P5 落地后已补齐 |
| 3D预览 r90 HTTP代理差异 | GLB响应 | 未知 | Three.js r90 + FastAPI/uvicorn 代理层交互导致 GLB 不加载（字节/headers 已对齐）。需抓包或升级 Three.js。
| 转换回调 JWT 过期风险 | `kafka_producer.send_conversion_order` | 未知 | userToken 透传上传时 token，长时间转换后可能过期。后续改为服务间 token |
| 装配同步未迁移 | `update_iteration` | P5+ | P1b 仅做零件单体，装配 BOM 同步仍在 Payara |
| 搜索为 DB 模糊匹配 | `search_parts` | P5+ | 无 ES 全文搜索，用 `ilike` 模糊匹配。不影响功能但性能随数据量下降 |

---

## 阶段依赖关系

后续阶段会解锁早期阶段的对齐债务：

- **P3（产品结构）** ✅ 已落地 → 配置项根零件 / 基线 / 替代品 检查已补齐
- **P4（变更管理）** ✅ 已落地 → 变更项检查已补齐
- **P5（工作流/通知）** ✅ 已落地 → PartRevisionDTO.notifications 字段已补齐

**所有对齐债务已全部清偿。**

---

## 已知风险（跨阶段）

- **REST API BasicAuth 401 未解决**：`admin:password` 经 BasicAuth 调 REST API 返回 401（JWT 正常）。影响依赖 REST API 认证的工具集成（如 CATIA Copilot sync）。根因未查清，当前绕过方案是直接 DB 操作。
- **WSL mirrored 网络重启后端口失效**：`wsl --shutdown` 重启可恢复，详见 REMINDERS。

## 持续合规工具

- **文件映射+代码级对比**（最可靠）: `docs/file-mapping.md` — 52 业务对 + 22 基础设施对，5 维度检查 (方法/SQL/异常/字段/Stub)。3 轮全量审计：60 对→35→11→14→0 问题。
- **全端点对拍 v2**: `scripts/full_compare_v2.py` — 96 端点 POST/PUT/DELETE/GET 全覆盖 + 种子数据 + 字段级 diff。用法: `python3 scripts/full_compare_v2.py`
- **对拍脚本 v1**: `scripts/compare_all_endpoints.py` — 133 GET 端点逐双后端 curl 对比。`--fresh` 模式清空→种子→对拍。
- **Stub 审计**: `scripts/audit_write_stubs.py` — 读-写-读一致性测试。
- **GET 尾斜杠**: `scripts/add_get_trailing_slash.py` — 自动补 GET 尾斜杠双路由。
- **双后端对比端口**: 8000=FastAPI，8005=Payara。
- **全量测试**: `pytest tests/ -q` — 142 passed

- **REST API BasicAuth 401 未解决**：`admin:password` 经 BasicAuth 调 REST API 返回 401（JWT 正常）。影响依赖 REST API 认证的工具集成（如 CATIA Copilot sync）。根因未查清，当前绕过方案是直接 DB 操作。规划涉及 REST API 认证的阶段前需先排查。
- **WSL mirrored 网络重启后端口失效**：`wsl --shutdown` 重启可恢复，详见 REMINDERS。

---

## 实际执行经验（从 P0/P1a/P1b/P2 执行中提炼）

**新阶段启动前必读本节。** 以下 bug 不是个别阶段的偶然问题——它们会在每个新阶段重复出现，因为根源相同。

### 防御性检查清单（每阶段实现端点后逐项检查）

**0. （新增）读前端 Model——提取响应必需字段。** 每个 POST 返回的 JSON 必须包含前端 Backbone model `parse()`/`initialize()` 中访问的所有字段。curl 对拍只比 HTTP 层，覆盖不了 `model.author.name` 这类 JS 层字段缺失导致的静默崩溃。**在写代码之前就搞清楚前端需要什么字段。**

1. **尾斜杠（Trailing Slash）**：前端 Backbone.js 的 `collection.create()` 会在 URL 后加 `/`。FastAPI 默认把 `/parts/` redirect 307 到 `/parts`，AJAX POST 不跟随 307 → **创建永远失败**。**每个 POST/PUT 端点必须同时注册带 `/` 和不带 `/` 的双路由。**

2. **前端发送 camelCase**：前端发 `standardPart`、`workspaceId`、`reference`（非 `standard_part`、`workspace_id`、`number`）。Pydantic v2 默认 case-insensitive 匹配可以应对简单字段，但 `populate_by_name=True` 仅在定义了 `alias` 时才生效。**DTO 字段要么用前端相同的 camelCase 命名，要么显式加 `alias`。**

3. **响应字段格式**：前端 Backbone model 的 `parse()` 方法依赖特定字段名和结构。零件需要 `partKey`/`partIterations`、文档需要 `id="{ref}-{ver}"` 格式 + `documentIterations` 数组。**缺少这些字段不会报错在 API 层，而是前端静默失败（窗口不关、列表不刷新）。**每阶段实现后必须用浏览器实测，不能只靠 pytest。

4. **缺失端点的 405 陷阱**：前端可能调用 spec 里没覆盖的端点（如 `checkedout`、`countCheckedOut`、`doc_revs`）。如果 Nginx 已把路径切到 FastAPI 但 FastAPI 没实现该端点，某个 `{id}` 参数化路由会误匹配并返回 400/405，前端显示红色错误条。**切 Nginx 之前必须确认该路径前缀下所有端点都已实现。**

### 最有效的调试手段

**Payara vs FastAPI 对拍**——对同一操作分别请求 Payara（`:8001`）和 FastAPI（`:8000`），比较响应体、状态码、header。P2 所有 bug 都是这样发现的。**建议把对拍写进每阶段的 definition of done。**

### 执行教训总结

| 教训 | 来源 | 防止方法 |
|------|------|----------|
| Nginx 在对齐审计之前切 → 前端炸 | P1a | 标准工作流：对齐审计→对拍→切 Nginx |
| 尾斜杠 307 导致静默失败 | P2 | 双路由注册 |
| 响应少字段导致前端静默异常 | P2 | 浏览器实测 + Payara 对拍响应体 |
| 缺端点误匹配为路径参数路由 | P2 | 全端点清单审查 |
| Workspace 重建导致种子测试数据丢失 | P2 | 测试数据独立于 workspace 操作 |
| SQLAlchemy flush 顺序不可靠 | P1b | 关联表 FK 声明 + 双 transaction 删除 |
