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
| FE-02 | 非 bug（数据残留） | :8000 parts 列表比 :8005 缺很多列 | GD50 残留列自定义数据 + Payara L2 缓存陈旧 | 已定位根因 |
| FE-03 | HIGH | 自定义零件表格列：可选属性列显示 "undefined"（应显示 Source/设计状态/材料） | 后端双路由遮蔽：List[str] 版本覆盖了对象数组版本 | 已定位根因+修法 |

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

---

## FE-02 — :8000 parts 列表比 :8005 缺很多列（非 bug：测试残留数据 + Payara 缓存假象）

**严重级**：非 bug（数据残留污染），无代码缺陷
**报告人**：用户（test1，`product-management/index.html#GD50/parts`）
**现象**：:8000 的零件列表只显示很少的列；:8005 同页面显示完整 10 列。

**根因**：GD50 在数据库里存有**零件列表自定义列配置**（残留测试数据），且两端口对该数据的可见性不同：

1. 数据事实（PostgreSQL 实查）：
   - `workspace_parttablecolumn`：GD50 → 仅 1 行 `pr.name`（order 0）
   - `workspace_documenttablecolumn`：GD50 → 仅 1 行 `name`（order 0）
2. :8000（FastAPI）`GET /workspaces/GD50/front-options` 如实返回
   `{"partTableColumns":["pr.name"],"documentTableColumns":["name"]}`（实测）。
   前端 `product-management/js/views/part/part_list.js:36`：partTableColumns 非空 → 走自定义列分支 → **只渲染"名称"1 列**。前端与 FastAPI 行为均正确。
3. :8005（Payara）同接口返回 `{"partTableColumns":[],"documentTableColumns":[]}`（实测）→ 前端 `part_list.js:39` fallback 到 `PartTableColumns.defaultColumns`（`common-objects/customizations/part-table-columns.js:139-142`，10 列全显）。
   Payara 返回空 = **JPA L2 缓存陈旧**（known-issues #4 已知架构问题）：该配置行是经 FastAPI 直写 SQL 落库的，Payara 缓存中的 `WorkspaceFrontOptions` 实体仍是空集合。
4. 结论：**:8000 显示的才是 DB 真实配置**，:8005 的"完整 10 列"反而是缓存假象。差异根源是残留的列自定义数据，来源无法精确追溯（表无时间戳；round-5 审计脚本 `audit_write_stubs.py` / `full_compare_v2.py` 均 PUT 过 front-options，UI 自定义页保存也写同表）。

**处置建议**：删除 GD50 在 `workspace_parttablecolumn` / `workspace_documenttablecolumn` 的残留行即可恢复默认 10 列显示（数据清理，非代码修复；删除操作需用户确认后执行）。

**顺带观察（非本 bug）**：本前端版本**没有文档列表列的自定义入口**——`workspace-management` 只有 `part-table-customizations.js`，全前端 JS 零引用 `documentTableColumns`；该字段是后端死字段（Java DTO + DB 表存在但 UI 不消费），文档列表列由模板写死。因此 GD50 的 `workspace_documenttablecolumn`="name" 残留行只能来自脚本/手工 API 调用，UI 无法产生也无法清除它（好在无任何消费方，无实际影响）。另注意 `PUT front-options` 为整体替换语义：零件列自定义页保存时只提交 `{partTableColumns}`（`part-table-customizations.js:134-136`），后端（Java `WorkspaceResource.java:823-826` 与 back-py `workspace_manager.py:361-376` 语义一致）会顺带清空 documentTableColumns——对 UI 无影响（无消费方），非迁移回归，不立案。

---

## FE-03 — 自定义零件表格列：新增列下拉显示 "undefined"（FastAPI 迁移回归）

**严重级**：HIGH（影响 3 个前端功能：列自定义、查询构建器、UDF 计算）
**报告人**：用户（test1，`workspace-management/index.html#/workspace/GD50/customizations`）
**现象**：恢复默认列后想新增列时，:8000 的可选项显示 `undefined`；:8005 正确显示零件中实际存在的自定义属性（GD50 有 Source、设计状态、材料 三项）。

**根因**：back-py 中 `GET /workspaces/{ws}/attributes/part-iterations` 存在**双路由定义，错误版本遮蔽了正确版本**：

1. `app/routers/workspaces.py:197-201`：`response_model=List[str]`，调 `workspace_manager.get_workspace_attributes_part_iterations()`（`workspace_manager.py:317-323`，只 `SELECT DISTINCT ia.name`）→ 返回**字符串数组** `["Source","材料","设计状态"]`（:8000 实测）
2. `app/routers/attributes.py:47-70`：返回**对象数组** `[{name, attributeType, lovName}]`（接近 Java，但 key 用 `attributeType` 而非 Java 的 `type`，且缺 `locked`/`mandatory`）
3. `main.py` 注册顺序：`workspaces.router`(:188) **先于** `attributes.router`(:194)，FastAPI 先注册先匹配 → **List[str] 版本生效，attributes.py 版本为死路由**

**Java 基准**：`AttributesResource.java:75-93` 返回 `List<InstanceAttributeDTO>`，:8005 实测
`[{"locked":false,"mandatory":false,"name":"Source","type":"TEXT"}, ...]`

**前端影响面**（3 个消费方全部期望对象数组 `{name, type}`，拿到字符串后取属性得 undefined）：
1. `workspace-management/js/views/part-table-customizations.js:90-94`：`attribute.name`/`attribute.type` → undefined → 下拉选项显示 "undefined"（**用户所报现象**）
2. `product-management/js/views/query_builder.js:257-273`：零件高级查询构建器的属性过滤条件全部 undefined → 属性查询不可用
3. `common-objects/views/udf/user_defined_function.js:86-98`：`attribute.type === 'NUMBER'` 恒 false → UDF 可用属性列表恒空

**姊妹端点同病**：`GET /workspaces/{ws}/attributes/path-data` 同样被 `workspaces.py:204-208`（List[str]）遮蔽 `attributes.py:73-91`（对象数组）；消费方 `query_builder.js:283-296` 同样受影响。

**修法（记录待 FIX-PLAN，未执行）**：
1. 删除 `workspaces.py:197-208` 的两个 List[str] 路由（`attributes_part_iterations`/`attributes_path_data`），连带删除 `workspace_manager.py:317-331` 两个只查 name 的 service 方法（确认无他处引用后）
2. 让 `attributes.py` 路由生效，并把 `_filter_attributes`（`attributes.py:39-43`）输出 key 从 `attributeType` 改为 `type`，补上 `locked: False`、`mandatory: False` 字段，完全对齐 Java `InstanceAttributeDTO`（dtype→type 枚举映射 `_DTYPE_TO_ATTR_TYPE` 已存在且正确）
3. 验证点：:8000 与 :8005 两接口响应逐字段一致；customizations 页可选项显示属性名并可保存；查询构建器属性条件可用；UDF NUMBER 属性可选
