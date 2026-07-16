# 第6轮审计 — 前端 Bug 追踪（用户报告驱动）

> 模式：**按需分析**。用户在 :8000（FastAPI back-py）实际操作前端时报告 bug，本轮只做**根因定位并记录**，不修复。统一修复留待后续 FIX-PLAN。

## 环境
- front :8000 → back-py:8000（FastAPI，生产主链路）
- front :8005 → back:8080（Payara Java EE，对比基准）
- 账号：test1/password（GD50 ws-admin）、admin/password（全局管理）、alice/password（普通用户）
- 基准 workspace：GD50

## 严重级汇总

| 编号 | 严重级 | 标题 | 根因层 | 状态 |
|------|--------|------|--------|------|
| FE-01 | HIGH | 新建工作区 `POST /api/workspaces` 返回 500，但工作区实际已创建 | 后端响应序列化（ResponseValidationError） | 已定位根因 |

## 发现编号规则
- `FE-XX`：前端触发、经根因定位的问题
- 严重级：CRITICAL（数据损坏/功能完全不可用）/ HIGH（核心流程报错但有 workaround）/ MED（次要功能异常）/ LOW（体验/文案）

---

## FE-01 — 新建工作区 500（响应序列化 bug，非业务失败）

**严重级**：HIGH
**报告人**：用户（test1 账号，:8000）
**现象**：test1 新建工作区时前端报
```
POST http://localhost:8000/docdoku-plm-server-rest/api/workspaces 500 (Internal Server Error)
main.js?rev=...:53
```
但**刷新页面后，新工作区实际已创建成功**。

**根因**：后端 `POST /workspaces` 的**响应序列化失败**（FastAPI `ResponseValidationError`），而非业务逻辑失败。DB 写入在 `db.commit()` 时已完成，异常发生在 commit 之后的响应模型校验阶段，因此工作区已落库、刷新可见。

back-py traceback（关键行）：
```
fastapi.exceptions.ResponseValidationError: 1 validation errors:
  {'type': 'extra_forbidden', 'loc': ('response', 'admin'),
   'msg': 'Extra inputs are not permitted', 'input': 'test1'}
```

**调用链与代码定位**：
1. 路由 `app/routers/workspaces.py:219`
   `@router.post("/workspaces", status_code=201, response_model=WorkspaceDTO)`
2. service `app/services/workspace_manager.py:29 create_workspace()`
   - `:85` `db.commit()` —— workspace / userdata / workspaceusermembership 三表全部提交（**此时工作区已持久化**）
   - `:94-95` 返回 dict 含 **5** 个键：`{"id", "description", "enabled", "folderLocked", "admin"}`
3. DTO `app/schemas/admin/workspace.py:7 WorkspaceDTO`
   - `:8` `model_config = ConfigDict(from_attributes=True, extra='forbid')`
   - 仅 4 个字段：`id / description / enabled / folderLocked`，**无 `admin`**
4. FastAPI 用 `WorkspaceDTO` 校验返回 dict → 多出的 `admin` 键因 `extra='forbid'` 被拒 → `ResponseValidationError` → HTTP 500

**Java 基准对照**：
`docdoku-plm-server-rest/.../dto/WorkspaceDTO.java:30-42` 同样只有 4 个字段（`id / description / folderLocked / enabled`），**也无 `admin`**。差异在于 Jackson 序列化对象时不会因源对象多字段报错，而 Pydantic `extra='forbid'` 会。所以这是 Python 迁移引入的回归。

**影响面**：任何成功创建工作区的调用都会命中（不限 test1）。前端每次建工作区都收到 500、需手动刷新才看到结果，属核心管理流程可用性缺陷。

**建议修复方向（留待 FIX-PLAN，本轮不改）**：
- **首选**：删除 `workspace_manager.py:94-95` 返回 dict 中的 `"admin": admin_login` 键，使返回体与 `WorkspaceDTO`（及 Java 基准）严格对齐。`admin` 信息不属于该响应契约，前端通过工作区列表另行获取。
- 备选（不推荐）：将 `WorkspaceDTO` 的 `extra='forbid'` 放宽为 `extra='ignore'`——会全局削弱该 DTO 的校验强度，可能掩盖其他字段错配，不建议。

**对拍状态**：:8005（Payara）建工作区应正常返回 201（Java 无此序列化限制），可作为回归确认点（尚未实测，按用户新模式仅记录）。
