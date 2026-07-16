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
| FE-01 | HIGH | 新建工作区 `POST /api/workspaces` 返回 500，但工作区实际已创建 | 后端响应序列化（ResponseValidationError） | ✅ 已修复（2026-07-16） |
| FE-02 | 非 bug（数据残留） | :8000 parts 列表比 :8005 缺很多列 | GD50 残留列自定义数据 + Payara L2 缓存陈旧 | 已定位根因 |
| FE-03 | HIGH | 自定义零件表格列：可选属性列显示 "undefined"（应显示 Source/设计状态/材料） | 后端双路由遮蔽：List[str] 版本覆盖了对象数组版本 | ✅ 已修复（2026-07-16） |
| FE-05 | HIGH | :8000 注册成功后跳转 `?denied=true`，提示"请先登录"（:8005 正常自动登录） | 后端注册端点未返回 jwt 响应头 + 漏插 usergroupmapping | ✅ 已修复（2026-07-16） |
| FE-04 | HIGH | CATIA-Copilot 查 GD50_Frame latest-revision 报 403（:8005 返回 200） | 双重缺陷：ACL 检查用平台 admin 而非工作区 admin + 空 ACL 残留数据 | ✅ 已修复（2026-07-16） |

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


---

## 修复记录（2026-07-16）

**FE-01**：删除 `workspace_manager.py` create_workspace() 返回 dict 中的 `"admin"` 键（WorkspaceDTO `extra='forbid'` 只允许 4 字段）。
实测：`POST /api/workspaces` → **201** `{"id":"FE01TEST","description":"fe01 verify","enabled":true,"folderLocked":false}`（测试工作区已删除）。

**FE-03**：
1. 删除 `app/routers/workspaces.py` 中遮蔽正式实现的两个 List[str] 路由（`attributes_part_iterations`/`attributes_path_data`）及 `workspace_manager.py` 中对应的两个只查 name 的 service 方法
2. `app/routers/attributes.py` `_filter_attributes` 输出 key `attributeType`→`type`，删除 `lovName: None`，补 `locked: False`/`mandatory: False`，对齐 Java `InstanceAttributeDTO`
实测：`GET /workspaces/GD50/attributes/part-iterations` → `[{"name":"Source","type":"TEXT","locked":false,"mandatory":false}, ...]`，与 :8005 Java 基准逐字段一致；`path-data` → `[]`。
验证：pytest 282 passed / 1 skipped 零回归；back-py 镜像已 rebuild + 容器重建。


---

## FE-04 — GET /parts/GD50_Frame/latest-revision 403（工作区管理员被 ACL 锁死）

**严重级**：HIGH
**报告人**：用户（CATIA-Copilot 客户端，报错文案由客户端生成）
**现象**：test1 查 `GET /workspaces/GD50/parts/GD50_Frame/latest-revision` → :8000 返回 403「您，test1，没有执行此操作的足够权限」；:8005（Payara）同请求返回 **200**。零件存在（partrevision GD50_Frame/A）。

**触发链（两个独立缺陷叠加）**：

**缺陷 A（主因）——ACL 旁路判定用错管理员语义**：
- Java 基准：`ProductManagerBean.hasPartRevisionReadAccess:3554-3556` = `user.isAdministrator() || isACLGrantReadAccess`，其中 `User.isAdministrator()`（User.java:84-86）= `login == workspace.admin_login`（**工作区管理员**）。test1 是 GD50 的 admin_login → Java 直接放行
- back-py：`app/routers/part.py:374` `is_admin = user_mgmt_service.is_account_admin(...)`（user_manager.py:442-445，查 `usergroupmapping groupname='admin'` = **平台全局管理员**）→ test1 非平台 admin → is_admin=False → 进入 ACL 检查
- `acl_factory.check_read_access:86-109` 已接收 `workspace_id` 参数但**从未使用**——本应在此做工作区管理员旁路

**缺陷 B（伴生）——空 ACL 残留锁死所有人**：
- DB 实况：GD50_Frame/A 的 `acl_id=63`，`acl` 行 enabled=true，但 `acluserentry`/`aclusergroupentry` 均 **0 条**（同期残留还有 ACLCFG-1977AE 的 acl 154 也是 0/0；来源为 round-5 审计脚本 PUT ACL）
- Java 基准：`PartResource.updatePartRevisionACL:440-443`——`acl.hasEntries()` 为空时调 `removeACLFromPartRevision`（**删除 ACL，回退为工作区级权限**）；DocumentResource.java:705-708 同语义
- back-py：`product_manager.update_part_acl:1771-1788` 无此分支，空 entries 时 `apply_acl`（acl_factory.py:13-50）清空旧条目、不写新条目、保留 enabled ACL 行 → 产生「谁都不在名单上」的锁死 ACL
- `check_read_access:96-109`：ACL 存在且 enabled、无 user entry、无 group entry → False → 除平台 admin 外全员 403
- **系统性**：`apply_acl` 共 15 处调用（parts/documents/folders/product_instances/workflow_models/milestones/change/templates/product_structure），全部缺「空 entries → 删 ACL」分支

**修法（记录待 FIX-PLAN，未执行）**：
1. **缺陷 A**：在 `acl_factory.check_read_access`/`check_write_access` 内用已有的 `workspace_id` 参数加工作区管理员旁路（`SELECT 1 FROM workspace WHERE id=:ws AND admin_login=:l`），对齐 Java `User.isAdministrator()`；所有调用点无需改动
2. **缺陷 B**：在 `apply_acl` 集中处理——user_entries 和 group_entries 均为空时：删除两表旧条目 + 删 acl 行 + 返回 None（调用点 `xx.acl_id = new_acl_id` 自然置 NULL），对齐 Java removeACL* 语义
3. **数据修复**：清理存量空 ACL——`UPDATE partrevision SET acl_id=NULL WHERE acl_id IN (SELECT a.id FROM acl a WHERE NOT EXISTS(SELECT 1 FROM acluserentry u WHERE u.acl_id=a.id) AND NOT EXISTS(SELECT 1 FROM aclusergroupentry g WHERE g.acl_id=a.id))` + 对 documentrevision 等含 acl_id 的表同理 + 删孤儿 acl 行（GD50 现查实至少 acl 63/154 两条空 ACL）
4. 验证点：test1 查 GD50_Frame latest-revision :8000 与 :8005 均 200；PUT 空 ACL 后 acl_id 置 NULL；非成员用户仍被 `_check_workspace_member` 拦截


---

## FE-04 修复记录（2026-07-16）

全部修改集中在 `app/services/factory/acl_factory.py`（调用点零改动）+ 存量数据清理：

1. **缺陷 A（ws-admin 旁路）**：新增 `_is_workspace_admin()` helper；`check_read_access` 和 `check_write_access` 在 `is_admin` 之后增加工作区管理员旁路（对齐 Java `User.isAdministrator()`）。`check_write_access` 原先仅在 `acl_id is None` 分支内做的 ws-admin 检查提升到函数顶部（消除重复）。
2. **缺陷 B（空 ACL 删除语义）**：`apply_acl` 开头判断两组条目均为空 → 删条目 + 清全部 11 张业务表的 acl_id 引用（`_ACL_REFERENCING_TABLES`，避免 FK violation）+ 删 acl 行 + 返回 None，对齐 Java `removeACL*`。返回类型改为 `int | None`，15 处调用点 `x.acl_id = new_acl_id` 自然置 NULL。
3. **附带发现并修复（原 500 潜伏 bug）**：`PUT /parts/{key}/acl` 走 `update_part_acl` 时 body 的 `userEntries` 是 ACLDTO 数组格式 `[{key,value}]`，直接传入 `apply_acl` 后 `.items()` 崩溃 → `AttributeError: 'list' object has no attribute 'items'` → 500（迁移以来一直存在，意味着零件 ACL 设置在 :8000 从未可用）。修复：`apply_acl` 入口新增 `_normalize_entries()`，同时兼容数组格式（走 `parse_acl_entries`）和 dict 格式（值支持 int / "FULL_ACCESS" 字符串）。
4. **数据清理**：存量空 ACL（acl 63/154）已按 11 张表清引用后删除。

**验证**（:8000，test1=GD50 ws-admin）：
- `GET parts/GD50_Frame/latest-revision` → **200**（原 403），与 :8005 对拍一致
- `PUT parts/GD50_Frame-A/acl` 带条目 → 204，acl 行 + 1 条 user entry 落库（原 500）
- `PUT parts/GD50_Frame-A/acl` 空条目 → 204，acl_id 置 NULL、acl 行删除、全库零空 ACL 残留
- pytest 282 passed / 1 skipped 零回归；镜像 rebuild + 容器重建


---

## FE-04 code review 跟进（2026-07-16）

subagent 全面 review 结论：**Ready to merge**，无 Critical。`_ACL_REFERENCING_TABLES` 11 表与 models 核对一致；15 处 apply_acl 调用点兼容。两项旧有遗留缺口已按用户指示修复：
1. `document_manager.py` update_acl 空 ACL 分支改为统一调 `apply_acl`（原先只删 entries 留孤儿 acl 行）；实测 PUT 空 ACL → 204 + acl 行删除（种子文档 ACLDOC-5514DF/A 的测试 ACL 在验证中被删，属用户已接受的 GD50 写操作）
2. `product_structure.py:669`、`change_manager.py:55/463/480` 补传 workspace_id，ws-admin 读旁路现全覆盖 6 处调用点

未处理（reviewer Minor/建议）：空 ACL 删除与 ws-admin 旁路的专项回归测试待补；`_perm_to_int(None)` 静默降级 FORBIDDEN；apply_acl 内部 commit 事务模式（既有设计，改动需动 15 处调用点）。


---

## FE-05 — 注册成功后未自动登录，跳转 denied=true（FastAPI 迁移回归）

**严重级**：HIGH（所有新注册用户受影响；且缺 usergroupmapping 行有跨后端连锁影响）
**报告人**：用户（TEST-PLAN T1-1 执行中）
**现象**：:8000 注册完成 → 跳转 `index.html?denied=true&originURL=%2Fworkspace-management%2Findex.html`，显示"请先登录"；console：`GET /api/accounts/me 401`。:8005 注册后正常自动登录进 workspace-management。

**故障链**：
1. 前端注册成功回调 `account-creation-form.js:131-134`：`localStorage.jwt = xhr.getResponseHeader('jwt')` → 跳转 workspace-management
2. back-py `POST /api/accounts/create`（`app/routers/accounts.py:39-48`）只建账号返回 DTO，**响应头没有 jwt** → `localStorage.jwt = null`
3. workspace-management 加载 → `GET /api/accounts/me` 无 token → 401 → 前端重定向 `?denied=true`

**Java 基准**（`AccountResource.java:145-198`）：注册成功且 `account.isEnabled()` 时 `responseBuilder.header("jwt", tokenManager.createAuthToken(...))` —— 注册即登录。

**伴生缺陷（数据完整性）**：Java `AccountDAO.createAccount:55` 会同时 `em.persist(new UserGroupMapping(login))`（默认组 `users`）。back-py `account_manager.py:27-44` create_account 只写 account+credential，**漏插 usergroupmapping**。DB 实查：test1/tom/admin 有组行（种子/Java 建），而 alice、bob、chenweibo、e、SEED-* 等 back-py 建的账号全部缺行。影响：① Java 侧 `getRole()` 返回 null，这些账号在 :8005 无法通过容器认证登录（跨后端不一致）；② back-py login（auth.py:39-40）mapping 缺失时 fallback 字面量 `"REGULAR_USER_ROLE_ID"`（应为 `"users"`，Java 常量值 UserGroupMapping.java:50）写进 JWT，组名错误。

**修法（记录待执行）**：
1. `app/services/account_manager.py` create_account：`db.commit()` 前补 `db.execute(text("INSERT INTO usergroupmapping (login, groupname) VALUES (:l, 'users')"), {"l": login})`（对齐 AccountDAO:55）
2. `app/routers/accounts.py` create_account：签名加 `response: Response`；创建成功且 enabled 后 `response.headers["jwt"] = create_token(acc.login, "users")`（需 `from app.core.security import create_token`），对齐 AccountResource 注册即登录
3. `app/routers/auth.py:40` fallback 字面量 `"REGULAR_USER_ROLE_ID"` 改为 `"users"`
4. **存量数据修复**：`INSERT INTO usergroupmapping (login, groupname) SELECT a.login, 'users' FROM account a LEFT JOIN usergroupmapping m ON m.login=a.login WHERE m.login IS NULL;`（给所有缺行账号补 users 组）
5. 验证点：:8000 注册新账号响应头含 jwt，自动进 workspace-management；该账号能在 :8005 登录；usergroupmapping 无缺行账号


### FE-05 修复记录（2026-07-16）

用户补充确认同根因现象：bob（back-py 注册）在 :8005 登录直接 500（Java getRole() 返回 null）。四点全修：
1. `account_manager.py` create_account 补插 `usergroupmapping(login,'users')`（对齐 AccountDAO:55）
2. `accounts.py` create_account 加 `response: Response`，enabled 账号响应头返回 `jwt`（create_token(login,'users')，对齐 AccountResource:187 注册即登录）
3. `auth.py` login fallback 组名 `"REGULAR_USER_ROLE_ID"` → `"users"`
4. 存量补数据：7 个缺行账号（alice/bob/chenweibo/e/SEED-20260712-*×3）已 INSERT users 组行

实测：:8000 注册 fe05test → 201 + jwt 头（groupName=users）；usergroupmapping 落库；bob 与 fe05test 在 :8005 登录均 200（原 500）；登录 token 访问 /accounts/me 200。pytest 282 passed 零回归，镜像已 rebuild。遗留：测试账号 fe05test 保留在库（delete_account 级联不全 P5-21，不冒险删）。
