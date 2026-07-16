# 全量审计重点清单（FastAPI back-py 对齐 Java/Payara）

> 本文汇总多个审计会话的实战经验，用于 Python 迁移版（`docdoku-plm-server-py`）对齐 Java/Payara（`docdoku-plm-server`）的全量审计。
> **核心原则**：以 Java 源码为功能对照基准，以 DB `information_schema` 为 schema 真值源，以 Payara 实际响应为格式真值源。**不信任何"已完成"标记，逐端点核对实际业务逻辑。**

---

## 一、审计要点（按类别去重合并）

### 1. 裸 SQL 的表名/列名真实性
每条 `text()` / `sql_text()` 的表名、列名都要对 `information_schema` 逐一核实，不能凭 ORM 属性名或直觉猜。高频错误模式：

- **表名臆造**：`workflow_usergroup`、`simplewebhookapp`、`tagsubscription`、`notification`、`prdinstiteration`、`component_partversion` 等根本不存在。
- **列名想当然的"加/漏下划线"**：`checkout_user_login` → 实为 `checkoutuser_login`；`creation_date` → `creationdate`；`pm.number` → `partnumber`。
- **连接表名错**：`partiteration_attr` → `partiteration_attribute`；`usage_link_cadinstances` → `partusagelink_cadinstance`。
- **实例表 vs 模板表混淆**：`attributetype`/`lov_name` 只在 `instanceattributetemplate`；`instanceattribute` 只有 `dtype`。
- **列本身不存在**：`pathtopathlink` 无 `name`/`workspace_id`。
- **写入/查询的表存在但业务语义错**：列名/表名拼写都对，但在错误的上下文使用（如把基线路径存储写到零件替代链接实体表 `partsubstitutelink` 而非 `@ElementCollection` 子表 `productbaseline_substitutelink`；把 `ackauthor_login`（确认人）当收件人过滤未读通知）。仅凭 `\d` 验证列存在性不够，还要**确认该列/表在此业务场景中是否就是 Java JPA 映射的目标**。

### 2. DTO 字段对齐
每个 Pydantic schema 与对应 Java DTO 逐字段对齐：

- **`extra='forbid'` 缺字段 → 422**；**`extra='ignore'` → 静默丢数据**；多余键/缺必填键/类型不符在序列化阶段抛 `ResponseValidationError` → 500（且 DB 事务可能已提交 → 数据不一致）。
- **camelCase alias 缺失 → 422**（前端 payload 对不上）。
- **字段类型对齐 Java 类型**：int ordinal vs enum 名（如 `type=0` → `LATEST`）、date 对象 vs ISO 字符串、`List[str]` vs `List[dict]`、单复数（`attachedFile` vs `attachedFiles`、`baselineType` vs `type`）、缺 `lifeCycleState`。
- **getter 派生字段也会被 JSON-B 序列化**：如 `ACLDTO` 的 `userEntries`/`groupEntries` 数组。对齐时别只看 private 字段，还要看 public getter。
- **DTO 字段推导逻辑**：如 `attributeType` 由 `dtype` 判别符经 instanceof 映射、`lovName` 被 filter 清空、`matrix` 数组 vs `m00-m22` 独立字段的桥接——Java 的 Dozer converter / 手工映射逻辑要在 Python 复现，不能直接读不存在的列。
- **验证脚本会把请求 CreationDTO 误映射到响应 DTO**，产生假 CRITICAL，需人工甄别。

### 2A. 路由层 `dict body.get()` 字段名与语义对齐
凡路由或服务直接接收 `body: dict`，必须以 **Java DTO 字段名 + 前端实际 JSON** 为输入真值源，逐字段核查 `body.get("...")` / `body["..."]`。不要只检查 Pydantic schema，因为很多端点绕过了 schema。

- **禁止自创输入字段名**：不得把 Java/前端的 `timeZone` 改成 `timezone`，不得把 `milestoneId` 改成 `milestone_id`，不得把 `language` 缩写成 `lang`。ORM/SQL 列名可继续用 snake_case，但 JSON 边界必须保持 Java DTO/前端字段名。
- **同名字段需按场景区分语义**：账号场景中 `password` 是旧密码（验证用），`newPassword` 才是要写入的新密码；共享链接场景中 `password` 又是正确字段。不能用全局字符串替换代替对照 Java 方法语义。
- **字段必须端到端穿透**：前端 JSON → FastAPI route → service 签名 → ORM/SQL 写入 → response。任何一层读到但未透传，或 service 签名未接收，都算 bug（本轮 `timeZone` 注册丢失即属此类）。
- **ACL 格式以 Java/前端为准**：ACL 输入输出为 `userEntries` / `groupEntries` 数组；`userEntriesMap` / `userGroupEntriesMap` 这类 Python 自创派生字段不得作为 JSON 契约。`ACLFactory` 语义中 workspaceId 是独立上下文参数，不得编码进 login key（如 `login:workspace_id`）。
- **辅助脚本**：`python3 scripts/check_body_field_names.py` 可检查路由层 `body.get()` 字段是否偏离 Java DTO 全量字段，并对 `timeZone`/`language`/`milestoneId` 等已知命名差异做防回归扫描。

### 3. 硬编码桩 / 假成功（最易漏）
搜 `return []`、`return {}`、`return {"id": 0}`、`return None`、`return 0`、`= False`、`pass`、`TODO`、`"stub"`、`succeed: True`（但无实际写库）。

- GET 端点硬编码返回空数组，根本没查库（`audit_write_stubs.py` 测不到，需 AST/grep 扫描）。
- `try/except: return []` 吞异常，把 404/500 吞成 HTTP 200 + 空数组，前端无法区分"空"和"错"。Java 从不这样做。
- 本会话实例：`instances`、`path-to-path-links-types`、产品结构树 `path`/`pulId`、importer 全 stub、query POST 返回 `{"id":0}`。
- **对照 Java 看该字段是否本应有真实查询**。

### 4. 级联删除 / JPA cascade 复刻
凡手写 raw-SQL 级联删除，都要对照**完整外键图**逐表核查：

- Java JPA `cascade`/`orphanRemoval` 自动清理关联表 + `BinaryResource` + vault 文件；Python SA 需逐个显式确认。
- **多对多 `secondary` 关系 SQLAlchemy 不支持 delete-orphan，必须显式删**。
- `delete_workspace` 曾漏约 40 张引用表（change/effectivity/pathdata/query/import/workflow/template 等）→ FK 500。
- **无 workspace_id 列的全局表**（`binaryresource` 主键 fullname、`instanceattribute`/`instanceattributetemplate` 经 join 定位、`documentlink`、`queryrule`）按 workspace_id 匹配不到 → 残留，需按前缀或 join 汇集 id 删。
- 反向排查：Python 是否有 Payara 不存在的**额外清理**（如误删 `usergroupmapping`）。
- 每个 `db.delete(x)` 反查 DB FK 约束，漏表如 `partiteration_attribute`。

### 5. INSERT 列完整性
Java JPA 自动写所有列（含 `dtype` 判别列）；Python raw SQL INSERT 必须对照 `information_schema` 确认：

- 所有 NOT NULL 列都赋值。
- 判别列（`dtype`）不遗漏。**写 instanceattribute 的所有路径必须统一写 dtype**（`importer._write_iteration_attributes` 写、`product_manager._sync_instance_attributes` 不写 → query_executor 按 `ia.dtype` 过滤检索不到）。

### 6. 权限检查逐行对比
Java 的 `hasWorkspaceWriteAccess`/`checkWorkspaceReadAccess`/`check_write_access` 等需**逐行读 Java 逻辑对比 Python**，不能只看方法名存在：

- 403 bug 常因漏了第一步短路判断。
- **null-ACL 分支**：`check_write_access(acl_id=None)` 类调用方漏传可选参数（如 `workspace_id`）→ 权限绕过。搜所有调用点核参数完整性（历史 BUG-46 同类）。
- **签出隐藏**：被他人 checkout 的末迭代应对其他用户隐藏，查询结果路径易漏。审计所有返回零件/文档迭代的端点。
- **大规模代码迁移后的权限回归**：当 router 内联逻辑被批量迁入 service 时（如 ~350 处迁移），核心 CRUD 端点的权限一般跟着迁入，但标签管理、obsolete、用户组管理等"非核心"端点的权限检查可能被系统性遗漏。审计重构后代码时，**不仅逐端点查，还要按端点类别（CRUD / 标签 / 权限管理 / 统计）分组对照**——同一类操作是否都保留了权限检查。

### 7. 异常抛出一致性
Java 抛什么异常，Python 应抛等价异常：

- service 层应抛领域异常（`FileNotFoundException`）而非硬编码 `raise HTTPException(404,...)`。对拍：`check_hardcoded_exceptions.py`。
- 异常类型对齐（`NotAllowedException` vs `AccessRightException`）、i18n key 的 `{0}` 参数不多不少。
- 对齐参照 `docs/superpowers/archive/migration-process/throw-matrix.md`。
- **`check_hardcoded_exceptions.py` 对位置参数版 `HTTPException(404,"...")` 有检测盲区**（只匹配关键字参数形式 `HTTPException(status_code=404,...)`）。人工补充：`grep -rn "HTTPException([34]" app/routers/`。

### 8. 数据格式与 NULL 容忍度
- **返回结构字段级对齐**：数组元素是 plain string 还是 `{key:value}` 对象（P2P types `["x"]` vs `[{"type":"x"}]`）；多值字段是逗号拼接还是数组。
- **NULL 容忍度差异**：Java 多处无 null 检查直接 NPE（`userGroupMapping.getGroupName()`、`getRotationMatrix().getValues()`）。逐个确认 Python 写入的 DB 字段是否可能为 NULL、Java 读取时是否会炸。重点：`rotationType=MATRIX` + `m00-m22` NULL、`usergroupmapping` 缺行、`partUsageLinkId` 为 None。
- **字段来源贯穿**：追踪每个 DTO 字段在 Python 中的构造逻辑，注意"schema 定义了但构造代码未赋值"。

### 8-bis. 内部常量/枚举字符串对齐
除 DTO 序列化字段外，service 层返回的**运行时字符串常量**也要对齐 Java：
- **holderType** 等路由决策字符串（`"part"` vs `"parts"`、`"workspace-workflow"` vs `"workspace-workflows"`）会被前端 JS 用作条件分支，单复数不一致导致页面组件/导航错误，但不会触发 schema validation 或 500。
- workflow status、effectivity type、baseline type 等枚举映射的字符串值同理。
- 审计方法：在 Java 端找到常量定义位置（如 `TaskManagerBean.setHolderType`），grep Python 侧全量引用点确认字符串值一致。

### 8A. Pydantic v2 forward-reference / OpenAPI 生成验证
拆分 schema 文件或给 schema 加 `from __future__ import annotations` 后，必须验证所有跨文件类型引用已 `model_rebuild()`。

- **触发方式**：`GET /docdoku-plm-server-rest/api/openapi.json` 会遍历所有 `response_model` 并生成 JSON Schema，能暴露 import 冒烟抓不到的 forward-ref 问题。
- **高风险模式**：`WorkflowDTO.activities: List[WorkflowActivityDTO]`、`WorkflowActivityDTO.tasks: List["TaskDTO"]`、`ActivityModelDTO.taskModels: List[TaskModelDTO]` 这类跨文件/字符串注解，若未在 `__init__.py` 中 rebuild，会导致 `/openapi.json` 500。
- **验证命令**：`curl -f http://localhost:8009/docdoku-plm-server-rest/api/openapi.json` 或 FastAPI TestClient 拉取 openapi。

### 9. 深拷贝 vs 浅拷贝（clone 语义）
所有"从上一版本创建新迭代/新版本"的复制逻辑（checkout、新 revision、模板→实例），核对 Java 是否 `clone()+persist`（新行新 id）。本会话 `instanceattribute` 浅拷贝导致跨迭代共享 → 更新时 FK 冲突。

### 10. 文件系统 / vault 操作
Java `storageManager.*`（`deleteWorkspaceFolder`/`renameData`/删文件）这类磁盘操作，Python 极易只做 DB 不做磁盘（或反之）。工作区/零件/文档/迭代删除路径都要查。

- **vault 路径格式**：正确格式**无 `geometry/` 子目录**（`{ws}/parts/{pn}/{ver}/{it}/{file}`）。核查所有 vault 路径构造函数与 Java `FileStorageProvider` 一致，清理错误的死代码函数。

### 11. path 参数穿透 / 查询分支
- **查询参数分支**：同一端点是否有多个行为分支（如 `configSpec` 有无走不同逻辑），Python 是否只实现了其中一个（`list_instances` 忽略了 `configSpec` 分支）。
- **path 参数穿透**：`instances`/`filter`/`decode-path` 接受 `path` 用于子树过滤，确认 Python 真实实现按 path 导航/过滤，而非忽略 path 返回全量。

### 12. 中间件 / 响应整形差异
全局中间件（ErrorCollector、TrailingSlash、URLDecode、UserLanguage）可能改变响应形态。审计端点输出时以"经中间件后的实际响应"为准，别只看 return 值。

### 13. 同步 vs 异步语义
Java 多处 `@Asynchronous`（如 `deleteWorkspace`）。Python 一般做成同步，确认不影响正确性（仅时序/性能差异），并在文档标注差异。

### 14. 事务与提交
- `get_db` 异常回滚、`begin_nested` savepoint 使用是否正确。
- 内部多次 commit 是否会留下半成品状态（如 checkout 后写失败留孤儿迭代）。
- `extra=forbid` 序列化 500 时 DB 事务可能已提交 → 数据不一致（见要点 2）。

### 15. 路由 / 注解 / 接线正确性
- **FastAPI 参数类型注解**：WebSocket 曾因缺 `: WebSocket` 注解被当 query 参数 → 403。核查所有 handler 参数注解与 `Depends` 注入（尤其 `db`/`current_user` 是否漏注入）。
- **路由路径三方一致**：核查每个 router 路径与 `front/nginx.conf`、前端 `App.config.apiEndPoint` 拼接吻合（尤其非 `/api` 前缀端点，如 `/ws`）。
- **`response_model` 正确性**：声明类型须与实际返回一致（`post_workspace_query` 曾误标 `response_model=dict` 实返 list；多态返回端点应不声明）。
- **函数归属**：路由层不应混入服务层逻辑。用 tracker.csv 交叉检查每个 Java class 方法映射到正确的 Python 文件，避免文件行数失衡（`part.py` 700 行 vs `instance_body_writer_tools.py` 200 行）。
- **dead code / service 未接线**：tracker.csv 映射的 service（如 `workspace_manager`）可能根本没被 router 调用，router 自己内联了逻辑。确认"映射的 service 是否真被调用"+"是否与 router 逻辑重复/不一致"。

### 15A. 前端 nginx / 部署接线审计
前端容器和反向代理也是接线的一部分，不能只审 FastAPI 路由。

- **nginx upstream 解析时机**：若某个上游容器可选启动（如 Payara `back` 已停用、`restart: "no"`），`proxy_pass http://back:8080` 这类静态 upstream 会在 nginx 启动时预解析，容器不存在会导致 front 启动失败。应使用 `resolver 127.0.0.11` + 变量 upstream（如 `set $back "back:8080"; proxy_pass http://$back;`）。
- **运行配置与镜像配置同步**：`docdoku-plm-docker/front/nginx.conf`（bind mount 运行配置）和 `docdoku-plm-front/docker/nginx.conf`（镜像内置配置）需要同时更新，否则 rebuild/去挂载后会回退。
- **location 兜底策略**：FastAPI 已接管全部 REST 端点时，未知路径应交给 FastAPI 返回标准 404，而不是 nginx `return 502` 掩盖真实路由状态。
- **systemd/启动脚本链路**：WSL/systemd 服务需检查 `ExecStart` 可执行性；脚本缺 `+x` 或未显式 `/bin/bash` 调用会导致重启后服务未拉起。

### 16. SQL 注入面
`query_executor` 曾把用户可控字段名 f-string 拼进 SQL。审计所有 `text()`：**列名/表名走白名单，值走绑定参数**。

### 17. 端点覆盖缺口
Java `*Resource.java` 有但 Python 缺（pathdata / path-to-path / import / query 执行引擎 / filter configSpec 解析）。用 Java 端点数 vs Python 端点数做 diff。

### 18. 只有数据存在才暴露的 bug
空表时 SQL/序列化都不报错，有真实数据才 500（GD50 有基线数据才暴露）。**审计必须在有真实数据的工作区（如 GD50）跑，不能只看空库。**
- **写入路径在 pytest 中通常无覆盖**——创建 PathData、创建基线等 POST/PUT 端点没有对应的集成测试，空库时也不报错。审计时应**对 information_schema 核实写入表的结构完整性**（列名/约束/FK），并在有数据环境中构造请求实际执行写入（不仅限于 GET 对拍）。

### 18-bis. Service 封装绕过（数据/路径/DB/配置直接访问）
Java 的封装链完整（REST→Bean→StorageManager→FileStorageProvider），Python 多处绕过 service 层直接访问底层资源。审计时 grep 以下模式：

- **vault 路径直接构造**：`Path(settings.VAULT_PATH)`、`_vault_root()`（绕过 `vault.py` 的公开路径函数）。Java `FileStorageProvider` 是所有 vault 操作的唯一入口；Python 有 40 处直接拼路径。应改为 `vault.part_attached_path` / `vault.part_nativecad_path` / `vault.template_attached_path` 等封装函数。缺失的类型需补加（文档、产品实例、workspace、导出 ZIP 等）。
- **Router 层直接 DB 操作**：`routers/*.py` 中的 `db.execute` / `db.query` / `db.add` / `db.delete` / `db.commit`。第 3 轮大重构已消除主路由的内联 DB，但 `change_orders.py`、`roles.py`、`export/*.py`、`workspace_memberships.py`、`part.py`、`document_templates.py`、`folders.py`、`document.py` 等仍有残留。应迁入对应 service 方法。
- **绕过 Depends(get_db)**：直接 `SessionLocal()`（`main.py:72` UserLanguageMiddleware、`services/file_export/instance_body_writer_tools.py:126`）。Java JPA EntityManager 通过 `@PersistenceContext` 注入，Python 应通过 `Depends(get_db)` 获取 session。
- **绕过 vault/binary_storage**：`services/binary_storage.py` 自己重定义了 `_vault_root()`（与 `vault.py` 重复）。应统一使用 `vault.py` 的函数。
- **绕过 config**：`from app.core.config import settings` 在 `routers/` 和 `services/` 中多处出现，仅为了读 `VAULT_PATH` 字符串（可随 vault 封装消除）。Java 配置通过 `@Resource` 注入，Python 应通过封装后的 service 函数间接获取。

### 19. tracker.csv 状态列不可信
tracker.csv 是**文件级映射**，只标 Python 对应文件是否存在。多处标"已完成"实为空壳/桩（`workspace_manager` stub、importer stub、query POST）。**审计要实际核对代码，不信 CSV 的"已完成"。**

### 20. 回调鉴权
conversion 回调用用户 JWT，长转换后可能过期。审计 service-to-service 回调的鉴权健壮性。

### 21. 状态码对齐
对照 loose-ends 记录的 MISMATCH（多为 Payara 自身 500 / 缺端点），确认 Python 侧 404/403/422/500 语义与 Java 一致，区分是 FA 侧 bug 还是 Payara 自身问题。

### 22. 测试脆弱性
测试勿硬编码可被删除的种子数据（`test_query_save` 依赖已删的"测试工作区"而失败）。审计测试的 seed 依赖。

---

## 二、已知检查手段

### 脚本工具

| 脚本 | 检查范畴 | 备注 |
|------|---------|------|
| `check_hardcoded_exceptions.py` | service 层 HTTPException 违规 | 一键 |
| `validate_dto_fields.py` | Java/Python DTO 字段差异（CRITICAL=extra=forbid 缺字段→422 / WARNING）| 已知缺陷：把请求 CreationDTO 误映射到响应 DTO → 假 CRITICAL |
| `validate_sql_columns.py` | 全部 `text()` 的列名/表名 + INSERT NOT-NULL 完整性 + 表存在性 | 已知误报：`ON CONFLICT DO UPDATE SET` 被当表名、自增 `id` NOT-NULL 误报 |
| `check_body_field_names.py` | 路由/服务层 `body.get()` 字段名 vs Java DTO 字段全集，防 `timeZone`/`language`/`milestoneId` 等命名偏移 | 只检查字段名，不能替代 Java 方法语义审查和 route→service 参数透传检查 |
| `audit_write_stubs.py` | POST/PUT/DELETE 写操作持久性 | 测不到 GET 空返回桩 |
| `compare_all_endpoints.py` | 158 端点状态码 + 错误文本 + 行为对比 | 需 Payara(back) 在线，back 已停用需先 `docker start docdoku-plm-docker-back-1` |
| `compare_with_payara.py` | 单路径 Python vs Payara 逐条 diff | `--login/--password`，默认 test1/password |
| `full_compare_v2.py` | 全 API GET 响应字段深度对比 | 需 Payara 在线 |
| `endpoint_behavior_test.py` | create→verify→delete 行为断言（约 10 项）| 一键 |
| pytest（`tests/`）| DTO 序列化 + service 逻辑单元/集成测试 | 见下方基线 |

### pytest 基线（先记住基线，只关注新增失败）
- 运行：`docdoku-plm-server-py/` 下 `venv/bin/python -m pytest -q`（或 `venv/bin/pytest -q`）。
- **基线数字随会话演进有出入**（历史记录见过 176 passed / 271~272 passed）；关键：约 **10–11 个失败是预存种子数据问题**（`test_products_api`、`test_product_structure_service`、`test_part_schemas`、`test_p5_models`、`test_parts_error_paths`、`test_query_save` 等），**非代码回归**。
- **审计前先跑一次记录基线失败集**，任何改动不得引入新失败。
- 分域测试文件：`test_query_executor.py`、`test_query_pbs.py`、`test_query_result_serialize.py`、`test_query_pathdata.py`、`test_query_save.py`、`test_query_run.py`、`test_excel_parser.py`、`test_attributes_importer_utils.py`、`test_import_record.py`、`test_importer_service.py`、`test_import_endpoints.py`。

### 运行时 / 冒烟验证
- **import 冒烟**：`venv/bin/python -c "import app.main"` —— 快速抓 schema forward-ref / 语法 / 导入错误。
- **schema 单测**：`venv/bin/python -c "from app.schemas... import X; X.model_validate({...})"`。
- **在线冒烟（curl）**：`BASE=http://localhost:8009/docdoku-plm-server-rest/api`；`POST /auth/login {"login":"test1","password":"password"}`（密码就是 `password`），**JWT 在响应头 `jwt`**；常用 `WS=GD50`。
- **健康检查**：`GET .../api/health` → 200。
- **Payara 对照 diff**（最硬验证）：Payara 直连 `:8001`、或 front Port 85（`:8005`）；FastAPI 直连 `:8009`——同一请求对比两边响应 JSON。
- **抓 traceback**：`docker logs --tail N docdoku-plm-docker-back-py-1`（500 真实堆栈，定位 `/app/app/...:行号`）；`/dev/errors` 端点（ErrorCollectorMiddleware 内存记录所有 4xx/5xx 的 req/res/user）。

### DB 真值源
- `postgres_query` MCP，或 `docker exec docdoku-plm-docker-db-1 psql -U changeit -d docdokuplm -c "\d 表名"` 核列名/数据量。
- 大结果集 MCP 会卡，优先 psql。
- 直查 `information_schema` + 实际数据佐证（查共享行、残留行）。

### 部署方式
- **rebuild（更干净、可复现）**：`docker build -t docdoku-plm-docker-back-py:latest .` + `docker compose up -d --force-recreate --no-deps back-py`。
- **热更新（权宜）**：`docker cp app/... docdoku-plm-docker-back-py-1:/app/app/... && docker restart docdoku-plm-docker-back-py-1`。

---

**给新会话的提醒**：审计前先跑一次 pytest 记录基线失败集；以 Java 源码（`docdoku-plm-server/`）为功能对照基准，但注意该目录未来会随 Payara 下线而移除。
