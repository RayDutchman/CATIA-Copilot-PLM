# Payara → FastAPI 完整迁移路线图

> **权威文档**：本文件是迁移路线图的唯一事实来源。取代散落在各 plan 文档和对话中的描述。每次规划新阶段前先读本文件。
> **最后更新**：2026-07-04

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
| **P0** | 基础设施（FastAPI 骨架、JWT、DB、vault、Kafka） | ✅ 完成 | `2026-07-04-fastapi-migration-p0-infrastructure.md` |
| **P1a-core** | 零件核心 CRUD（ORM + 14 端点 + 签出签入 + BOM 更新） | ✅ 完成 | `2026-07-04-fastapi-migration-p1a-parts-core.md` |
| **P1a-align** | 零件行为对齐（i18n 基础设施 + 7 方法错误消息 + DTO 字段） | ✅ 完成 | `plans/2026-07-04-payara-fastapi-parts-alignment.md` |
| **P1b** | 零件文件（nativecad 上传下载 + 附件 + 转换回调 + release/obsolete/tags + 搜索） | ⬜ 待规划 | — |
| **P2** | 文档与文件夹（Documents/Folders/Tags/文档模板） | ⬜ 待规划 | — |
| **P3** | 产品结构（Products/ConfigurationItems/Baselines/ProductInstances/3D 装配树） | ⬜ 待规划 | — |
| **P4** | 变更管理（ChangeIssues/ChangeRequests/ChangeOrders/Milestones） | ⬜ 待规划 | — |
| **P5** | 工作流与权限（Workflow/WorkflowModel/Tasks/ACL/角色/用户组/Webhook/通知） | ⬜ 待规划 | — |

### 当前 Nginx 路由

```
/docdoku-plm-server-rest/api/auth/                         → FastAPI back-py:8000  （P0 已切）
/docdoku-plm-server-rest/api/workspaces/{ws}/parts...      → FastAPI back-py:8000  （P1a 已切）
其余全部                                                     → Payara back:8080
```

---

## 对齐债务追踪

跨模块约束/字段因属主模块未迁移而暂时打桩，等属主阶段落地时补齐：

| 债务 | 位置 | 属主阶段 | 说明 |
|------|------|----------|------|
| deletePartRevision: 配置项根零件检查 | `product_service.delete_revision` | P3 | `EntityConstraintException1`，需 ProductConfiguration 表建模 |
| deletePartRevision: 基线检查 | 同上 | P3 | `EntityConstraintException5`，需 ProductBaseline 表 |
| deletePartRevision: 替代品检查 | 同上 | P1b/P3 | `EntityConstraintException22`，需 PartSubstituteLink 表 |
| deletePartRevision: 变更项检查 | 同上 | P4 | `EntityConstraintException21`，需 ChangeItem 表 |
| PartRevisionDTO.notifications | `part_mapper.map_revision` | P5 | 当前始终空列表，需 ModificationNotification 表 |

---

## 阶段依赖关系

后续阶段会解锁早期阶段的对齐债务：

- **P3（产品结构）** 落地后 → 补齐 parts 删除的配置项根零件 / 基线检查
- **P4（变更管理）** 落地后 → 补齐 parts 删除的变更项检查
- **P5（工作流/通知）** 落地后 → 补齐 PartRevisionDTO.notifications 字段

规划这些阶段时，务必在计划中包含"回补对齐债务"任务。

---

## 已知风险（跨阶段）

- **REST API BasicAuth 401 未解决**：`admin:password` 经 BasicAuth 调 REST API 返回 401（JWT 正常）。影响依赖 REST API 认证的工具集成（如 CATIA Copilot sync）。根因未查清，当前绕过方案是直接 DB 操作。规划涉及 REST API 认证的阶段前需先排查。
- **WSL mirrored 网络重启后端口失效**：`wsl --shutdown` 重启可恢复，详见 REMINDERS。
