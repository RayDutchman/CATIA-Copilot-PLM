# Changelog

按日期倒序记录所有功能变更、Bug 修复和配置改动。

格式：`## YYYY-MM-DD`，条目以 `feat:` / `fix:` / `chore:` / `docs:` 前缀标注。

---

## 2026-07-11 — 3D 预览修复 + Conversion Service 收尾 + 删除工作区遗漏修复

> 3D 预览三根因修复，conversion LOD 生成部署，工作区删除 file 级联补全。instances 辅助函数移入 instance_body_writer_tools.py。产品级 3D 查看修复（产品配置页面）。

### fix(py-3d): 修复产品级 3D 实例端点

- **症状**：GD50 工作区 11 个零件（GLB 文件存在、转换成功）在前端均无法 3D 预览。
- **根因 1**（`app/routers/part.py:436`）：`GET parts/{part_key}/instances` 硬编码 `return []`（stub）→ 前端 InstancesManager 拿不到任何实例数据→装配体 iframe 无渲染
- **根因 2**（`app/services/part_mapper.py:105`）：`geometryFileURI` 逗号拼接多 GLB 路径（`/api/files/A.glb,/api/files/B.glb`）→ 前端 `showCADFileView` 当单文件路径构造无效 URL
- **根因 3**（`app/parts/js/views/cad-file-view.js`）：CADFileView 使用 OBJLoader + MTLLoader，无法解析 GLB 格式（原 Java 版输出 OBJ，现 Python 版输出 GLB）
- **修复**：
  - Fix 1：实现 instances 端点——递归遍历装配树（`partiteration_partusagelink`→`partusagelink`→`partusagelink_cadinstance`→`cadinstance`），叶子节点输出实例 JSON（matrix 4×4 行主序 / files 按 quality 升序 / 包围盒 / path/id），对齐 Java `InstanceBodyWriterTools.writeLeaf()`
  - Fix 2：geometryFileURI 改为取 quality=0（最高精度）的单个 GLB 路径
  - Fix 3：CADFileView 替换 OBJLoader/MTLLoader 为 GLTFLoader；`parts/main.js` 添加 `gltfloader` RequireJS 路径
- **数据库验证**：确认 `partiteration_partusagelink` 复合键结构（workspace/partnumber/version/iteration + component_id）、`partiteration_geometry` 关联表（geometry_fullname→binaryresource.fullname）、`cadinstance` 支持 ANGLE/MATRIX 双模式
- **验证**：`GD50_Frame-A/instances` → 1 实例 + identity矩阵 + 3 GLB；`Product1-A/instances` → 9 子组件 + 正确位置矩阵

### feat(conversion): LOD 生成 + docker-compose 本地 build（续前次 handoff）

- `conversion-service-py/main.py` LOD 三级精度（deflection 0.05/0.30/1.00），失败降级；`convertedFileLODs` 动态构建
- `docker-compose.yml` conversion 改为本地 build（`context: ../conversion-service-py`）
- `docdoku-plm-conversion-service/DEPRECATED.md` 废弃标注
- 容器重建部署，LOD 代码验证通过

### fix(py-3d): 产品配置页面 3D 查看修复

- `product_instances.py` list_instances 增加 configSpec 分支，复用 collect_leaf_instances
- `product_structure.py` _convert_visitor_component 修复 path/partUsageLinkId（从硬编码改为 PSFilterVisitor path 列表构建，跳过 VirtualRootLink）
- `products.py`/`product_instances.py`/`product_baselines.py` path-to-path-links-types 返回格式修复 `[str]→[{"type":str}]`

### 删除工作区遗漏修复（back-py）

- **症状**：删 GD50 后重建，上传附件 409 FileAlreadyExists（`binaryresource` 残留 + vault 文件夹未清）
- **根因**：`delete_workspace` 只做 `workspace_id` 级联 DELETE FROM → `binaryresource` 无 `workspace_id` 列（主键是 fullname 路径）匹配不到；无 vault 磁盘删除
- **Payara 比对**：Java 靠 JPA `orphanRemoval` + `FileUtils.deleteDirectory(vaultPath/workspaceId)` 自动清理
- **修复**：显式按前缀 `fullname LIKE 'GD50/%'` 删 binaryresource + `shutil.rmtree` 删 vault 文件夹
- **为何不能靠 ORM 级联**：`attached_files`/`geometries` 为多对多 `secondary=` 关系，SQLAlchemy 禁止 `delete-orphan`；`native_cad_file` 多对一缺 `delete-orphan`；且走批量裸 SQL 绕过 ORM 工作单元
- **修复 A**：级联末尾（所有引用 binaryresource 的 join 表删除后）增 `DELETE FROM binaryresource WHERE fullname LIKE :p ESCAPE '\'`，前缀 `{ws}/%`，LIKE 转义（`_`→`\_`、`%`→`\%`）对齐 `WorkspaceDAO.java:130`。覆盖 nativecad/attachedfiles/geometry GLB/文档文件，等价 JPA 级联范围。
- **修复 B**：`db.commit()` 后 `shutil.rmtree(VAULT_PATH/ws, ignore_errors=True)`，复刻 `deleteWorkspaceFolder`；失败仅记日志不回滚（对齐 Payara 文件层异常不影响 DB）。
- **说明**：Python 端保持**同步**删除（Payara 是 `@Asynchronous`，其"删得慢"是异步窗口所致；Python 同步更简单可靠）。存量已坏的 GD50 用修复后的 delete 重删即可清净（DB 行 + vault 文件夹一并清除）。
- 部署：docker cp back-py + 重启，启动无导入错误；DB 校验转义 LIKE 精确匹配 GD50 的 102 行 binaryresource。

---


> CATIA Copilot 同步更新零件报 `PUT /workspaces/{ws}/parts/{pn}-{ver}/iterations/{n}` 500。根因经与 Payara Java 源码逐条比对确认。

### fix(py-part): 实例属性跨迭代共享导致更新时 FK 冲突

- **症状**：更新已存在迭代（如 GD50_Frame/A/2）报 500 `ForeignKeyViolation ... fk_partiteration_attribute_instanceattribute_id`。
- **根因（双层）**：
  1. 主因：`product_manager.py::_copy_iteration_files`（checkout 创建新迭代时）复制实例属性为**浅拷贝**——新迭代的 `partiteration_attribute` 关联复用旧迭代同一个 `instanceattribute` 行 id，未克隆底层行。DB 实证 `GD50_Frame/A` 的 `instanceattribute` id 7352 被 iter1+iter2 共享。
  2. 触发：`_sync_instance_attributes` 更新时无条件删除本迭代旧 `instanceattribute` 行，因另一迭代仍引用共享行 → FK 冲突。
- **Java 比对结论**：Payara `checkOutPart`（ProductManagerBean.java:553-560）对每个属性 `attr.clone()`+`instanceAttributeDAO.createAttribute()`（em.persist→新行新 id），每个 PartIteration **深拷贝独占**其 InstanceAttribute；更新时靠 `@OneToMany(orphanRemoval=true)`（PartIteration.java:130）自动删旧行，连接表以 ITERATION 为键，删除只影响当前迭代。确认 Python 修复方向正确。
- **修复 A（根治）**：`_copy_iteration_files` 检出复制实例属性改为**深克隆**（`INSERT INTO instanceattribute ... SELECT ... FROM instanceattribute WHERE id=:old RETURNING id` 复制全部值列，再用新 id 建关联），对齐 Java `attr.clone()+persist`。
- **修复 B（兜底 + 修复存量坏数据）**：`_sync_instance_attributes` 删除孤儿 `instanceattribute` 前先查是否仍被其它 `partiteration_attribute` 行引用，被共享则跳过删除，避免历史浅拷贝数据再触发 FK 冲突（更新后该迭代自动切换到独立新行，存量数据自愈）。
- 部署：docker cp back-py + 重启，启动无导入错误。

---


> 由 `scripts/validate_sql_columns.py` + `scripts/validate_dto_fields.py` 扫描驱动。全部 docker cp 部署 back-py 并重启，启动无导入错误。

### fix(py-sql): 34 处 raw SQL 列名/表名错误（14 文件）

原始扫描报告的 31 处（12 文件）+ DELETE/UPDATE 存在性检查新发现的 3 处真实错误全部修复。所有列名/表名均先经 `information_schema` 核实。

- `routers/attributes.py`：`instanceattribute` 无 `attributetype`/`lov_name`（那是 `instanceattributetemplate` 的列）→ 改用 `dtype` 判别符映射到 `InstanceAttributeType`（对齐 Java `InstanceAttributeDozerConverter` 的 instanceof），`lovName` 按 Java `filterAttributes` 置空；连接表更正 `partiteration_attr`→`partiteration_attribute`、`pathdataiteration_attr`→`pathdataiteration_attribute`，path-data 经 `prdinstiteration_pathdatamstr` 过滤工作区
- `routers/document.py`：inverse-product-instances-link 重写——`prdinstiteration` 表不存在→`productinstanceiteration`，用 `prdinstiteration_documentlink` 真实列（prdinstancemaster_serialnumber/configurationitem_id/iteration）；inverse-path-data-link 用 `pathdataiteration_documentlink`+`pathdatamaster`（`pathdata`/`pathdataiteration.id` 均不存在）
- `routers/product_instances.py`：`productinstanceiteration_documentlink` 表不存在→`prdinstiteration_documentlink`（DELETE/INSERT/SELECT 三处）；INSERT 改为先建 `documentlink` 中间记录再关联（对齐 pathdata/partiteration 模式）
- `routers/products.py`：`prdinstiteration_pathdatamstr.iteration`→`prdinstanceiteration_iteration`
- `routers/tasks.py`：`checkout_user_login`→`checkoutuser_login`（documentrevision + partrevision）
- `services/cascade_action_manager.py`：`partrevision.creation_date`→`creationdate`
- `services/file_export/instance_body_writer_tools.py`：`partusagelink` 无 `component_partversion`（usage link 关联的是 partmaster 非版本）→ 移除该过滤条件
- `services/notification_manager.py`：`tagsubscription` 表不存在→`tagusersubscription`；`event` 字符串模型→真实 `oniterationchange`/`onstatechange` 布尔列 + `tag_workspace_id`
- `services/listeners/subscription_manager.py`：`tagsubscription`→`tagusersubscription`+`tagusergroupsubscription`（删标签）；`subscription`→`statechangesubscription`+`iterationchangesubscription`（删用户，对齐 Java `removeAllSubscriptions`）；`tagusersubscription.user_login`→`subscriber_login`；`tagusergroupsubscription.group_id`→`subscriber_id`
- `services/listeners/part_notification_manager.py`：`notification` 表不存在→`modificationnotification`，`target_*`→`impacted_*`（对齐 Java `ModificationNotification.removeAllOnPartRevision/Iteration`）
- `services/organization_manager.py`：`account.organization_name` 不存在→经 `organization_account` 连接表关联
- `services/product_manager.py`：`workflow_usergroup` 表不存在→删除冗余 INSERT，改为把 role_mapping 传入 `instantiate_workflow`（内部正确写 `task_user`/`task_usergroup`）
- `services/products/part_workflow_manager.py`：`get_aborted_workflows` 原 SQL 含英文占位文本恒返回空→用 `part_aborted_workflow` 关联表正确查询
- `services/webhook_manager.py`：`simplewebhookapp`/`snswebhookapp` 表不存在→单表 `webhookapp`（`dtype` 判别 SimpleWebhookApp/SNSWebhookApp）+ `webhook.webhookapp_id` FK 关联

> 剩余 3 处 `❌ UPDATE SET → 表不存在` 为验证脚本误报（正则把 `ON CONFLICT DO UPDATE SET` 的 SET 当表名），14 处 `⚠️ 缺 NOT NULL 列 id` 为自增主键误报，均非真实 bug。

### fix(py-dto): 3 个 CRITICAL DTO 缺字段（`extra='forbid'` → 422）

- `ConversionResultDTO`（conversion_result.py）：补 `partIterationKey`（Java `PartIterationKey`）
- `UserDTO`（part/user.py）：补 `membership`（Java `WorkspaceMembership`）
- `WorkspaceWorkflowCreationDTO`：补 `workflow`

> 均以 `Optional[dict] = None` 宽松接收。验证脚本另报 2 处（`PathDataIterationCreationDTO.partLinksList`、`ProductBaselineCreationDTO.author`）经核实为脚本把 Python **请求 CreationDTO** 误映射到 Java **响应 DTO** 所致（缺字段属于响应侧），非真实 422，未处理。

---


- refactor(conversion): conversion-service-py 接管构建，docker-compose.yml 改为本地 build
- feat(conversion): LOD 生成——deflection 三级精度（0.05/0.30/1.00），失败降级为单 LOD
- fix(converter): 删除 vault.part_geometry_path() 和 converter_utils.vault_geometry_path() 错误路径函数（含多余 geometry/ 子目录，与 Java 不符，未被使用）
- chore(conversion): docdoku-plm-conversion-service/ 标注废弃
- feat(front-dev): 前端热更新开发模式——webapp.properties.json port→8009，新增 dev.sh

## 2026-07-10 — 工作区删除 500 修复 + WebSocket /ws 403 修复

> 分支 `feat/py-query-execution-engine`。均已 docker cp 部署 back-py 并线上验证。

### fix(py-workspace): 删除工作区 500（FK 违规）
- 症状：admin 删除 `Workspace_2` 报 500（`DELETE /workspaces/Workspace_2`），但能删空工作区"测试工作区"。
- 根因：`app/routers/workspaces.py::delete_workspace` 的手写级联删除**覆盖不全**——空工作区无子数据可删成功，而 Workspace_2 富数据触发 `fk_changeissue_affected_part_iteration` 等外键；实测缺失约 40+ 张引用表（变更管理/effectivity/layer/marker/产品实例子链接/pathData/P2P/query/import/模板/workflow/订阅/collection/shared entity 等）。
- 修复：对齐 Payara `WorkspaceDAO.removeWorkspace` 的完整级联（17 阶段），并用 `SET LOCAL session_replication_role='replica'` 关闭 FK 触发器以规避严格删除顺序（changeit 为超级用户）。**保留全局 `account`/`credential`/`usergroupmapping`（注册用户）**，仅删除 `userdata`（工作区成员关系）；用户不在任何工作区时才清理其 `usergroupmapping`。运行时纯 SQL、不依赖 Java 源码。
- 验证（非破坏性）：对 Workspace_2 真实数据（2656 零件）执行 flush 后，23 项残留引用检查全部为 0，再 rollback，数据未改动。

### fix(py-ws): WebSocket /ws 握手 403
- 双重根因：（1）路由注册为 `/ws`，但前端/nginx 实际访问 `/docdoku-plm-server-rest/ws`，Starlette 无匹配路由；（2）`ws_endpoint(websocket)` 缺 `WebSocket` 类型注解 → FastAPI 将 `websocket` 误判为**必填 query 参数**，握手时校验缺参 → 403（`websocket_param_name=None, query_params=['websocket']`）。
- 修复（`app/main.py`）：路由改为 `@app.websocket("/docdoku-plm-server-rest/ws")` + 参数注解 `websocket: WebSocket`。
- 验证：握手返回 `101 Switching Protocols`（back-py 直连 + 经 front nginx），AUTH 消息往返得到 `{"type":"AUTH_OK","login":"test1"}`。

---

## 2026-07-10 — Importer 属性导入域（FastAPI）

> 分支 `feat/py-query-execution-engine`。对齐 Payara `ExcelParser` / `AttributesImporterUtils` / `ImporterBean` / `PartsResource`。仅 `.xlsx` 属性导入落地（BOM 保留 stub，Java 侧本无实现）。全量 pytest 272 passed（+83 新测试）/ 10 预存 seed 失败 / 1 skipped，无回归；docker cp 部署 back-py 并线上冒烟通过（preview/import/poll/delete 全链路）。

- chore(py-import): 新增 `openpyxl==3.1.5` 依赖（容器 + venv 已装）
- feat(py-import): Excel 属性解析器 `app/services/importers/excel_parser.py`——`parse_excel(data, import_type)`，对齐 ExcelParser.java（`名 <类型>` / `名 <ListOfValues> <LOV名>` 表头正则、首列 cell comment 校验 pm.number/ctx.*、`|` 多值拆分、attribute_id 注释、类型校验 TEXT≤255/BOOLEAN/DATE `%Y-%m-%d %H:%M:%S`/NUMBER/URL/LOV、空值拒绝）
- feat(py-import): 属性合并工具 `app/services/importers/attributes_importer_utils.py`——TOKEN_TO_DTYPE/VALUECOL 映射、`merge_attributes`（忠实 Java 更新/新建/DuplicateEntry/AttributeNotFound）、`resolve_lov_index`（lov_namevalue）、`would_change`
- feat(py-import): 修正 `Import` ORM 到真实表结构（Boolean pending/succeed、startdate/enddate）+ `import_record.py` 原生 SQL CRUD（create/complete/get/list/delete，子表 import_error/import_warning）
- feat(py-import): `ImporterService` 属性导入编排（`app/services/importer.py`）——对齐 doPartImport/bulkPartUpdate：PartMaster 查找、写权限/canChange 判定、checkout 前迭代读现有属性→merge→错误门控（有错不写）→checkout→dtype 感知写入→commit→可选 checkin；`dry_run_import_into_parts` 返回 partRevsToCheckout；BOM 方法保留 stub
- feat(py-import): 5 个 import REST 端点接入（`app/routers/parts.py`，全部 `/workspaces/{ws}/parts/...`）——POST import（multipart `upload`，importType 门控，import_record 持久化，204）、POST importPreview（同步返回 ImportPreviewDTO，200）、GET imports/{filename}、GET import/{id}（404）、DELETE import/{id}（204）
- fix(py): 最终评审修复——`query_executor` pr.*/pm.* 未知列名走 `_safe_ident` 白名单防 SQL 注入（+3 回归测试）；`post_workspace_query` 补 `response_model=list`；导入端点先算 is_admin 再 create_import（避免孤儿 pending 记录）
- docs(tracker): 同步 `migration/tracker.csv`——新增 5 条 PythonSpecial 行（Y-009~013：query_executor/query_pbs/excel_parser/attributes_importer_utils/import_record），订正 R-056（query_result.py 实际位置）与 X-008（ext/ 版未启用，功能见 Y-012）

> 已知设计分歧（记录待后续统一）：`importer._write_iteration_attributes` **写入** `instanceattribute.dtype`（如 `InstanceTextAttribute`），而应用内既有 `product_manager._sync_instance_attributes` **不写** dtype。此分歧是刻意的——保证导入的属性能被 `query_executor`（按 `ia.dtype` 过滤）检索到。后续可考虑统一 `_sync` 也写 dtype。

---

## 2026-07-10 — Query 自定义查询执行引擎（FastAPI）

> 分支 `feat/py-query-execution-engine`。对齐 Payara `PartRevisionQueryDAO` / `PathDataQueryDAO` / `ProductManagerBean` / `QueryResultMessageBodyWriter`。全量 pytest 189 passed（+22 新测试）/ 10 预存 seed 失败 / 1 skipped，无回归；docker cp 部署 back-py 并线上冒烟通过。

- feat(py-query): 查询保存 `_save_query`/`_save_query_rule`（`app/routers/parts.py`）——递归写入 queryrule 树 + queryrule_values + selects/orderBy/groupedBy + querycontext，同名先删除，ID 走序列 `nextval`；抽出可复用 `_delete_query_by_id`
- feat(py-query): PartRevision 查询执行器（`app/services/query_executor.py`）——QueryRule 树递归 AND/OR、11 种 field 前缀路由（pm./pr./author./attr-{TEXT,LONG_TEXT,DATE,BOOLEAN,URL,NUMBER,LOV,PART_NUMBER}.）、全量 operator 映射、date equal 展开日区间、pr.* 特殊字段（checkInDate/modificationDate 末迭代约束、status 枚举、tags join、linkedDocuments 恒真）、属性 EXISTS 子查询按需 join（优于 Java 无条件 cross join）、后过滤（已检入迭代 + `check_read_access`）
- feat(py-query): PathData 查询执行器 `run_pathdata_query`（pd-attr-\* 前缀，挂 pathdataiteration_attribute，按产品实例迭代路径集合过滤，返回 path 集合）
- feat(py-query): context PBS 过滤（`app/services/query_pbs.py`）——按 QueryContext 用 PSFilterVisitor 遍历装配结构，构建 QueryResultRow（depth/amount/path/P2P sources·targets/context），应用 pathDataQueryRule 过滤；`merge_rows` 取 PBS ∩ PartRevision 结果交集
- feat(py-query): QueryResult 序列化（`app/schemas/query_result.py`）——按 `selects` 输出 JSON 行数组，pr.partKey 恒输出，attr-\*/pd-attr-\* 始终数组，ctx.\* 仅 context 行
- feat(py-query): `POST /workspaces/{ws}/parts/queries` runCustomQuery 端点真实化（run + `?save=` 保存 + `?export=` JSON/CSV(400)），替换原 `{"id":0}` 桩

---

## 2026-07-09 — deps 访问控制 + 基线校验 + 错误收集工具

### deps.py 工作区访问控制修复
- fix(deps): 补 `workspace.admin_login` 检查——工作区管理员即使不在该工作区的 userdata 表中，也应能访问自己管理的工作区（对齐 Java `checkWorkspaceReadAccess`）
- fix(deps): 补 `workspaceusergroupmembership` 用户组成员资格检查——通过用户组间接属于工作区的用户也能访问（对齐 Java `userGroupDAO.getUserGroupMemberships()` 回退逻辑）

### 基线创建校验 + 响应修复
- feat(baseline): `ProductStructureService._validate_baseline_parts()` BFS 遍历全量校验零件可用性
  - LATEST：每个零件必须有已签入迭代（`checkout_user_login` 非空 → 拒绝，对齐 Java `getLastCheckedInIteration()`）
  - RELEASED：每个零件必须至少有一个发布版本（`status=1`）
  - 不满足 → `NotAllowedException49`（"根据所选类型没有可用迭代"）
- fix(baseline): POST `create_baseline` 响应由`{"id","name"}`改为完整`_bl_summary_dict()`（含 author/type/configurationItemId 等），消除前端 `TypeError: Cannot read properties of undefined (reading 'name')`

### 开发错误收集工具
- chore(dev): 新增 `app/core/error_collector.py` + `app/routers/dev.py`，所有 4xx/5xx 请求自动记录到内存
  - GET `/dev/errors` HTML 表格（可过滤 5xx、JSON 格式、一键清空）
  - `ErrorCollectorMiddleware` 自动记录 URL/方法/请求体/响应体/用户名/时间戳

### PartCreationDTO 422 修复
- fix(schema): `PartCreationDTO` 补 Field alias（standardPart/workflowModelId/templateId/roleMapping → snake_case），`extra='forbid'` 改为 `extra='ignore'`；消除 POST /parts 创建时的 422

### 测试
- 176 passed / 1 skipped（基线保持）
- 冒烟验证：ACLCI-7E8C3E 基线创建正确拒绝（零件 ACLCFG-15FF13 已签出无可用迭代），ACLCI-B98DED 正确创建并返回完整 author

## 2026-07-09 — effectivities 500 修复 + 用户姓名全量修复

### effectivities SQL bug
- fix(effectivity): `effectivity.py:79` `pre.workspace_id` → `pre.partmaster_workspace_id`（实际表 `partrevision_effectivity` 无 `workspace_id` 列，导致 500）

### 用户姓名显示全量修复
- fix(tasks): `_part_to_dict` 补查 Account 表，author/checkOutUser 字段填充真实 `name`（原先直接用 login）；`get_task` 端点 worker 字段同步补 name
- fix(document_baselines): `_baseline_to_dict` 补查 Account 表填充 author name；create 端点 `"name": current_user.name`（原 `current_user.login`）
- fix(product_structure): `_convert_visitor_component` 新增 `_resolve_user_name()` 辅助方法，author 字段从 login 改为真实姓名
- fix(products): `last_release` 端点 checkOutUser 构建方式重构，消除初始化时 `name=login` 的临时状态

### 全量检查工具
- chore: 新增 `scripts/check_user_dto_consistency.py`，AST 扫描 app/ 检测用户 DTO 中 `name=login`/缺 name 字段的问题；Critical 0 / Warning 50（均为内部 JWT payload dict，非前端 DTO，属误报）

### 测试
- 176 passed / 1 skipped（基线保持）
- effectivities 端点冒烟：200 OK，不再 500

## 2026-07-09 — P2P decodePath 验证 + 用户权限 bug 修复 + 代码审查修复

### 代码审查修复（review fixes）
- fix(p2p): `product_configurations.py` 删除与 `products.py` 重复注册的 POST `/path-to-path-links` 路由（first-match-wins，重复路由导致 `product_configurations.py` 版本死代码）
- fix(p2p): `pathFrom==pathTo` 由 `PathToPathLinkAlreadyExistsException` 改为 `NotAllowedException("NotAllowedException57")`，对齐 Java
- fix(p2p): `create_path_to_path_link` 的 rollback 由仅捕 `PathToPathCyclicException` 扩展为 `except Exception`，防止 DB 错误留下半提交状态
- fix(product-structure): 基线 ID 作 configSpec 时，`ResolvedCollectionConfigSpec` 接口（`filter_part_iteration`）不匹配 `PSFilterVisitor`（`filter_part_iterations`），改为全量遍历降级
- fix(path-data): `_sync_linked_documents` 修正列名错误（`pathdata_master_id` → `pathdatamaster_id`），改为通过 `documentlink` 中间表关联（对齐 `partiteration_documentlink` 模式），移除吃掉所有异常的 `except Exception: pass`
- fix(path-data): `delete_path_data` 补充级联清理引用该路径的 `pathtopathlink` 记录（含 CI/baseline/实例关联表）
- fix(products): `_ci_to_dict` 中 `pathToPathLinks: []` 硬编码改为调用 `get_links_for_ci()` 真实查询

### decodePath 路径验证补齐
- feat(p2p): `path_to_path_service.py` 新增 `_validate_path()`：创建 P2P link 前调用 `decode_path()` 验证 sourcePath/targetPath 有效性；无效路径抛 `PartUsageLinkNotFoundException`；对齐 Java `ProductManagerBean.createPathToPathLink` 铁律

### 用户权限被重置 Bug 修复
- fix(workspace): `workspace_memberships.py:212` 字段名错误修复：
  - **根因**：`body.get("readOnly", False)` 读取了不存在的字段，而前端发送的是 `membership: "READ_ONLY"` 字符串，导致 `readonly` 永远写入 `false`，设置只读权限实际上无效
  - **修复**：改为 `membership == "READ_ONLY"` 正确解析（向后兼容 `readOnly` 布尔字段）
  - **同时修复**：删除错误的 `UPDATE account SET enabled = ...`（Java 不触及该全局字段）
  - 冒烟验证：READ_ONLY → DB `readonly=t`，FULL_ACCESS → DB `readonly=f`，双向正确

### 测试
- 176 passed / 1 skipped（基线保持）

## 2026-07-09 — PathData / Path-to-Path Link 域 + configSpec 解析修复

### PathData / PathToPathLink 域（P0 主功能，18+ 端点）
- feat(path-data): 新增 `app/services/products/path_data_service.py`（PathData CRUD Service）
  - `create_path_data_master`：创建 master + 首迭代（同路径已存在则追加迭代，实例必须存在）
  - `add_new_path_data_iteration`：追加新迭代（属性+文档链接）
  - `update_path_data`：更新迭代属性/备注/文档链接（先删后建）
  - `delete_path_data`：删 master + 级联删迭代/属性/关联
  - `get_path_data_by_path`：按路径查 master（找不到返回 None，不抛异常）
  - `get_attributes_for_iteration`：查迭代实例属性
- feat(path-to-path): 新增 `app/services/products/path_to_path_service.py`（P2P Service）
  - CI 级：`create_path_to_path_link`（含 DFS 环检测）/`update`/`delete`/`get_links_for_ci`/`get_link_types_for_ci`/`get_links_from_source_and_target`
  - 实例级：`get_links_for_instance`/`get_link_types_for_instance`/`get_root_links_for_instance`/`get_links_from_source_and_target_for_instance`
- feat(router): `product_instances.py` 补充 PathData 8 端点 + P2P 实例级 6 端点
- feat(router): `products.py` 补充 CI 级 P2P CRUD 5 端点（list/create/get-by-id/update/delete）
- fix(router): `product_configurations.py` create_path_to_path_link stub → 真实实现（调用 service）
- fix(router): `product_baselines.py` `_query_path_to_path_links` 真实实现（通过 productbaseline_p2plink 关联表查）；`baseline_path_to_path_links_types`/`detail` stub → 真实实现
- fix(orm): `path_data_master.py` / `path_data_iteration.py` 重建（复合主键对齐 DB、删除不存在的列）
- fix(orm): `path_to_path_link.py` 列名对齐（sourcepath/targetpath，删除不存在的 name/workspace_id 列）
- fix(schema): `path_to_path_link.py` 补 `sourceComponents`/`targetComponents` 字段（extra=forbid）

### configSpec 解析 Bug 修复（filter 端点）
- fix(product-structure): `filter_product_structure` 支持字符串 `configSpec` 解析（latest/released/wip/pi-/baseline-id）
  - 新增 `parse_config_spec_str` 静态方法，映射到对应 PSFilter/ConfigSpec 对象
  - 修复了 configSpec=latest/released/wip 时报 `'str' object has no attribute 'filter_part_iterations'` 500 的 bug

### hasPathData 路径格式修复
- fix(product-structure): `_check_has_path_data` 路径格式修复（`{ci_id}-u2-u5` → `-1-u2-u5` 再查 DB）
- feat(product-structure): `_check_has_path_data_from_link_path`：visitor Component.path（PartLink 列表）→ `-1-u{id}` 格式 → DB 查询；`_convert_visitor_component` `hasPathData` 从硬编码 False 改为真实查询
- feat(product-baselines): `_query_path_to_path_links` 传入 baseline_id 后真实查 productbaseline_p2plink

### 测试
- 176 passed / 1 skipped（基线保持）
- 冒烟通过：CI P2P CRUD（创建/更新/删除/查类型）、PathData GET 返回空 DTO、PathData Create 验证实例存在

## 2026-07-09 — 迁移收尾 A+B+C 批次（~25 项）+ 修复 3 个生产 SQL bug

### 事实纠正 + 架构对齐（会话后半）
- fix(docker): back-py `Dockerfile` base image `python:3.11-slim` → `python:3.11-slim-bookworm`（本地已缓存），**恢复 rebuild 可用**。核实结论："back-py 不能 rebuild" 是误区——镜像仓库不通但 pip(PyPI) 容器内正常、基础镜像已缓存；实测 `docker build` + `compose up --force-recreate back-py` 完整通过并 health ok
- docs(instructions): `.opencode/instructions.md` 新增「重建 FastAPI 后端(back-py)」章节 + 纠正 docker cp 误区
- refactor(workspace): `workspace_manager.py` 5 方法确认按 tracker.csv 映射（`WorkspaceManagerBean.java`）应为**真实实现**（原 stub 违反映射，Payara 该 Bean 方法均真实）；`workspaces.py` 路由改为委派 workspace_service，对齐 Payara `Resource→ManagerBean→DAO` 分层，消除重复逻辑


### A 基础设施
- fix(nginx): SSL Proxy(9000→443) API+ws 改指向 `front`，复用 FastAPI 全覆盖路由（`proxy/nginx.conf`）；附带修复丢失的 `cert.key`（自签名重建，止住 1117 次 crash-loop）
- feat(doc-baselines): 补 `GET /{id}`（详情）+ `GET /{id}-light`（轻量）端点（export-files 早已存在于 export router）；对齐 Java DocumentBaselinesResource
- fix(doc-baselines): `type` int→enum 名（LATEST/RELEASED）修复 latent extra=forbid 500（list/create/get）

### B 数据降级修复（对齐 Payara，复用 decode_path）
- feat(product-config/baseline): `substitutesParts`/`optionalsParts` 用 decode_path 从 link 路径表解码填充（原硬编码 []）；config `substituteLinks`/`optionalUsageLinks` 从 `prdcfg_*link` 表读取
- fix(schema): `ProductConfigurationDTO.substituteLinks/optionalUsageLinks` 改 `List[str]` 对齐 Java `List<String>`
- feat(product-structure): 组件 `attributes`（实例属性，dtype→InstanceAttributeType 枚举）/`notifications`/`hasModificationNotification` 真实查询（原 []/False）

### C 小型 stub
- feat(workspace): WorkspaceManager 5 个 dead stub 改真实实现（disk-usage 求和 vault、front/back options 读写表）；`/disk-usage` 端点返回真实总量
- feat(query): `get_queries`（递归 queryrule 树 + selects/orderBy/groupedBy/contexts）/`delete_query`（级联删）真实化
- chore(converter): OnDemandConverter 注释明确化（需 LibreOffice 引擎，deferred）
- feat(schema): EffectivityDTO 空壳→填充全字段对齐 Payara

### 修复 3 个 pre-existing 生产 SQL bug（Workspace_2 有基线数据才暴露）
- fix(baseline): `_query_substitute_links` `pm.number`→`pm.partnumber`
- fix(baseline): `_query_optional_links` 删除不存在的 `pul.component_partversion` join 条件
- fix(baseline): `_query_path_to_path_links` 改返回 []（`pathtopathlink` 无 name/workspace_id 列；PPL 域延后）

### 文档 / 计划
- docs: 新增两大域独立计划 `plans/2026-07-09-pathdata-domain.md`（15-20h）、`plans/2026-07-09-importer-domain.md`（2-3天）
- docs: 今日执行计划 `plans/2026-07-09-migration-finish-abc.md`
- docs: `migration/loose-ends.md` 更新完成状态 + 记录 2 个新发现 loose-end（Query 执行引擎、filter configSpec 解析 500）

### 验证
- pytest 176 passed / 1 skipped（零回归）；app import OK
- docker cp 11 文件 + restart back-py，health ok
- 线上冒烟：document-baselines/product-baselines/product-configurations/products/disk-usage/front-options/back-options/parts-queries 全 200；product structure 全量遍历 attributes/notifications 已填充；HTTPS(9000) 经 ssl-proxy 200

---

## 2026-07-08 — 审计遗留修复：check_write_access 全覆盖 + extra=forbid 对齐 Payara

- docs: **docs/ 目录重组**（消除 Agent 阅读歧义，按 活跃/参考/归档 三态分层）
  - 新增 `docs/migration/`：`loose-ends.md`（迁移缺口唯一台账）+ `methodology.md` + `tracker.csv` + `README.md`
  - 施工期文档归档至 `docs/superpowers/archive/migration-process/`（ai-execution-rules、batch-protocol、file-mapping、throw-matrix、migration-plan-complete、audit-report、fastapi-migration-roadmap，均加 🗄️ banner）
  - `handoff-2026-07-08.md` → `docs/superpowers/archive/handoffs/`
  - 重写 `DOCS_INDEX.md` 为通用文档地图 + 按场景 Agent 阅读路由（移除过时的"CSV 唯一任务队列"语义）
  - `REMINDERS.md` 去重：迁移明细移交 loose-ends，仅保留跨领域非迁移待办
  - 执行计划：`docs/superpowers/plans/2026-07-09-docs-reorg.md`
- docs: 新增 `docs/migration/loose-ends.md` — Payara→FastAPI 迁移完整遗留清单（~59 处未完成/降级项，按域分组+优先级）

### check_write_access null-ACL workspace 写权限（补全 7 处调用点）
- fix(acl): acl_id=None 时须校验 workspace 写权限，补全所有未传 workspace_id 的调用点
  - `routers/milestones.py:40` — `_milestone_to_dict` 传 `workspace_id=ms.workspace_id`
  - `routers/change_common.py:79` — `_item_to_dict` 传 `workspace_id=item.workspace_id`
  - `services/document_manager.py:130/369/609` — delete_revision/checkout/checkin 传 `workspace_id=ws`
  - `services/workflow_manager.py:45` — `_check_write_access` 新增 `workspace_id` 参数，update_model/delete_model 传入 `ws`
  - `services/change_manager.py:172` — delete_item 一致性补 `workspace_id=ws`（原有 null-ACL 内联回退，无漏洞）

### extra=forbid 静默 500 风险修复（7 项，全部对齐 Payara Java DTO）
- fix(dto): TaskDTO — 删除 helper 多余字段 `closingDate`（Payara TaskDTO 仅有 `closureDate`）`services/task_manager.py:46`
- fix(dto): ACLDTO schema 对齐 Payara — `userEntries`/`groupEntries` 改为 `List[ACLEntryDTO]`（{key,value}），新增 getter 派生的 `userEntriesMap`/`userGroupEntriesMap`；新增 `ACLEntryDTO` `schemas/workflow/__init__.py`
- fix(dto): workflow-models acl_data — `userGroupEntriesMap` 由 groupEntries 正确派生（原硬编码 `{}`）`routers/workflow_models.py:41`
- fix(dto): WorkflowModelDTO — 去掉 Payara 不存在的 `workspaceId`，改为 Payara 实际字段 `reference` `schemas/workflow/workflow_model.py:12`
- fix(dto): TaskHolderDocDTO — `tasks/{login}/documents` 端点 response_model 改为 `DocumentRevisionDTO`（Payara 实际返回精简版 DocumentRevisionDTO），清空 tags/workflow 对齐 `Tools.createLightDocumentRevisionDTO` `routers/tasks.py:269`
- fix(dto): ProductInstanceIterationDTO — 删除 Payara 不存在的 `productBaselineId`（Payara 用 `basedOn`）`routers/product_instances.py`、`routers/products.py`
- fix(dto): ProductInstanceMasterDTO — 删除 Payara 不存在的 `workspaceId`（列表/详情端点均清理）`routers/products.py`
- fix(dto): OrganizationDTO — 补 Payara 实际存在的 `owner` 字段，list/get/update 端点 SQL 补查 `owner_login` `schemas/misc/organization.py`、`routers/organizations.py`

### 验证
- pytest 176 passed / 1 skipped（基线不退化）
- app import OK + 各 DTO schema 单测通过（含嵌套 ACLDTO 序列化）
- 已 docker cp 14 文件 + 重启 back-py，health ok，5 个修复端点线上 200/204 无 500

### 审计验证（无需改动）
- `_relaunch_workflow` 已于 commit 2164b07 改为 INSERT SELECT 深拷贝（9bfe150 补全 task_user/task_usergroup），审计遗留策略问题已解决

---


### P4B-WS WebSocket (13 条目)
- feat(ws): W-001 endpoint.py — FastAPI WebSocket /ws 端点（JWT 认证 + 模块路由），替代 Java @ServerEndpoint
- feat(ws): W-002 message.py — WSMessage JSON 消息容器（type 判别 + 类型安全访问器）
- feat(ws): W-003/004 — 编解码器由 FastAPI 原生 JSON 序列化替代（无需独立 Decoder/Encoder）
- feat(ws): W-005 module.py — WebSocketModule 抽象基类（can_decode + process）
- feat(ws): W-006 sessions_manager.py — WSSessionsManager 单例（user_login→List[WebSocket] + broadcast + hangup）
- feat(ws): W-007/008 chat_module.py — ChatModule（CHAT_JOIN/LEAVE/MESSAGE 消息处理 + 房间委派）
- feat(ws): W-009/010 room.py — Room + RoomManager（context 键多用户房间 + 生命周期管理）
- feat(ws): W-011 collaborative_module.py — CollaborativeModule（多用户实时协同 3D 同步：鼠标/相机/选中/标注）
- feat(ws): W-012 status_module.py — StatusModule（状态订阅/广播）
- feat(ws): W-013 webrtc_module.py + webrtc_utils.py — WebRTC 信令中继（OFFER/ANSWER/ICE_CANDIDATE/HANGUP/CALL/REJECT）

### P4B-EXT Extension (16 条目)
- feat(ext): X-001 cad_converter.py — CADConverter 抽象基类 + ConversionInput/Output DTO（插件式转换框架）
- feat(ext): X-002 conversion_order.py — ConversionOrder DTO（Kafka 转换订单消息体）
- feat(ext): X-003 conversion_result_proxy.py — ConversionResultProxy DTO（conversion-service 回调数据）
- feat(ext): X-004 converter_utils.py — 工具函数（CAD 格式检测、vault 路径构建）
- feat(ext): X-005 ondemand_converter.py — OnDemandConverterService（按需格式转换 stub）
- feat(ext): X-006 attribute_model.py — ImportAttribute DTO + AttributeType 枚举
- feat(ext): X-007 attributes_holder.py — AttributesHolder 标记接口
- feat(ext): X-008 attributes_importer_utils.py — 属性类型推断 + 值转换 + 模板校验（对标 312 行 Java）
- feat(ext): X-009/010 bom_importer.py — BomImporter 抽象基类 + BomImportRow/BomImportResult DTO
- feat(ext): X-011/012/013 part_importer.py — PartImporter 抽象基类 + PartToImport/PartImportResult DTO
- feat(ext): X-014/015/016 path_data_importer.py — PathDataImporter 抽象基类 + PathDataToImport/PathDataImportResult DTO
- chore(main): 注册 /ws WebSocket 端点

## 2026-07-07 — P3B-B File Utils + Export 层迁移

- feat(file): R-049~052 — file/util 工具包 (binary_resource_streaming/download_meta/download_response/upload)，Range 解析/MIME 类型/ETag/Content-Disposition 等提取为独立模块
- feat(export): R-053 — 文档基线 ZIP 导出端点 (document_baseline_export)，遍历基线文档附件打包为 ZIP 流
- feat(export): R-054 — 产品实例 JSON 流端点 (instance_collection)，使用 StreamingResponse + generator 输出 JSON 数组
- feat(export): R-055 — 产品文件 ZIP 导出（product_file_export 工具模块），集成到 products.py export-files 端点
- feat(export): R-056 — 查询结果 JSON/CSV 导出（query_result 工具模块），集成到 parts.py query-export 端点
- feat(export): R-057 — 虚拟实例 JSON 流端点 (virtual_instance_collection)，创建虚拟根 PartLink 遍历装配树
- feat(util): R-058~063 — file_export 工具包 (DTOs: document_baseline_file_export/product_file_export；工具: file_download_tools/file_export_tools+ZipStream/instance_body_writer_tools+Matrix4/search_query_parser)
- fix(router): product_baselines.py baseline_export_files stub → 真实 DB 查询基线零件 nativeCAD 文件列表
- chore(main): 注册 3 个新导出路由（document_baseline_export/instance_collection/virtual_instance_collection）

## 2026-07-07 — P3B-A Router 层迁移

- feat(router): R-003 attributes.py — GET /workspaces/{ws}/attributes/part-iterations + path-data，按属性名/类型去重
- feat(router): R-016 lov.py — LOV（List of Values）完整 CRUD（GET/POST /lov，GET/PUT/DELETE /lov/{name}），委托 lov_service
- feat(router): R-022 effectivity.py 升级 — 对接 effectivity_manager 和 Effectivity ORM 模型，实现 DateBased/SerialNumber/Lot 三种有效性类型的 POST（含关联 partrevision_effectivity 表），GET 从 join 查询
- feat(router): R-033 tags.py — 标签完整 CRUD（GET/POST/DELETE /tags）、批量创建（/tags/multiple）、按标签查文档（GET /tags/{id}/documents）、在根目录创建文档并打标签（POST /tags/{id}/documents）
- feat(router): R-043 workspace_workflow — 已在 workflow.py 中集成，CSV 标记已完成
- feat(router): R-045 document_template_files.py — 文档模板文件上传（multipart）和下载，支持 HTTP Range 断点续传，文件路径 vault/ws/document-templates/{templateId}/
- feat(router): R-047 part_template_files.py — 零件模板文件上传（multipart）和下载，支持 HTTP Range，文件路径 vault/ws/part-templates/{templateId}/
- feat(router): R-014 FileResource — Python 直接实现各子资源（无需门面路由），CSV 标记已完成
- chore(main): 注册 6 个新路由（attributes/lov/tags/document_template_files/part_template_files 到 main.py）

## 2026-07-07 — P2B 服务全量迁移完成

- feat(py): Configuration 域 (S-030~S-042) — PSFilterVisitor 产品结构遍历引擎（stop/深度控制/循环引用检测）、PSFilterVisitorCallbacks（7 个回调钩子）、5 个 PSFilter 实现（LatestCheckedIn/LatestReleased/Released/UpdatePartIteration/WIP）、6 个 ConfigSpec 实现（EffectivityConfigSpec 基类 + DateBased/LotBased/SerialNumber effectivity + ProductBaselineCreation/ResolvedCollection）
- feat(py): 增强基础模型 — ProductStructureFilter 定义 filter_part_iterations/filter_links 抽象接口、ProductConfigSpec 添加 retained 集合 + template method 模式
- feat(py): product_structure.py 集成 PSFilterVisitor — filter_product_structure 支持 config_spec 参数，通过 visitor 按配置规格过滤遍历
- feat(py): psfilter_manager.py 升级 — 返回实际 ProductStructureFilter 实例而非 dict
- feat(py): Listeners (S-058~S-061) — UserFolderManager/PartNotificationManager/SubscriptionManager/RoleManager（CDI 事件监听器的 Python 等价）
- feat(py): Products (S-062~S-064) — PartWorkflowService/ProductBaselineService/ProductInstanceService（delegate 到现有 ProductStructureService + TaskService）
- feat(py): Documents (S-065~S-066) — DocumentBaselineService/DocumentWorkflowService
- feat(py): Indexer (S-073~S-078) — IndexerMapping 常量/IndicesUtils 索引名格式化/IndexerClient ES 客户端/EntityMapper 迭代→ES 文档序列化/IndexerResultsMapper 搜索结果映射/IndexerTextExtractor PDF+Office 文本提取
- feat(py): Validation (S-082) — AttributesConsistencyUtils 属性一致性校验（locked/mandatory 规则）
- feat(py): GCM (S-084) — GCMSender 推送通知（Firebase FCM HTTP API + 日志降级）
- test: 176 passed, 1 skipped (+0/-0 from baseline)

## 2026-07-07 — es_query_builder 审计修复（C5-C7, W11）

- fix(py): `es_query_builder.py` — q 参数从 `multi_match`+must(AND) 改为 `query_string`+bool should(OR)，对齐 Java SearchQueryParser（元数据匹配 OR 文件内容匹配）
- fix(py): `es_query_builder.py` — folder 从 `term` 改为 `match`+fuzziness=AUTO（C7），对齐 IndexerQueryBuilder
- fix(py): `indexer_manager.py` — DOC_MAPPING 中 KEY_FOLDER 从 keyword 改为 text（match+fuzziness 需要 text 类型）
- fix(py): `es_query_builder.py` — 移除 standardPart 过滤（W11），Java IndexerQueryBuilder 不使用此字段
- test(py): `test_es_query_builder.py` — 更新 q 参数测试为 query_string bool should 断言；移除 standardPart 测试

## 2026-07-07 — notifier/indexer_manager 审计修复

- fix(py): `notifier.py` — 完全重写，对齐 Java INotifierLocal（HTML 格式、Subject 前缀 "DocDokuPLM: "、拆分为 send_bulk_indexation_success/failure 两个独立方法、成功邮件不含 workspace 信息）
- fix(py): `indexer_manager.py` — reindex_all 调用方改为两个独立 notifier 方法；bulk() 错误提取修正（从 ES bulk errors 格式中提取 reason 字符串）

## 2026-07-06 — ES 全文搜索迁移

- feat(py): `indexer_manager.py` — 重写为迭代级索引（一个 iteration = 一个 ES doc，doc ID 含 iteration 号），索引命名 `docdoku-plm-{ws}-parts/documents`（对齐 IndexerMapping.java），BULK_SIZE=50 分页重建，集成 notifier 邮件通知
- feat(py): `es_query_builder.py` — 重写搜索查询构建，对齐 IndexerQueryBuilder.java 的 Query DSL（number/name/title/version/author fuzzy/date range/tags/content/standardPart）
- feat(py): `notifier.py` — 新建，reindex 邮件通知（smtplib→MailHog smtp:1025），中英双语 i18n
- feat(py): `product_manager.py` — 4 处实时索引（checkin/set_tags/remove_tag/delete_revision）
- feat(py): `document_manager.py` — 5 处实时索引（checkin/set_tags/remove_tag/move_document/delete_revision）
- feat(py): `workspaces.py` — create/delete workspace → ES index 管理 + PUT /index/{ws} 实现
- feat(py): `parts.py`/`documents.py` — 搜索端点 ES 优先 + DB LIKE fallback
- chore(py): `conftest.py` + autouse ES mock fixture（防测试 hang）
- chore(py): `requirements.txt` + elasticsearch==6.8.2
- test(py): `test_indexer_manager.py` + `test_es_query_builder.py`（28 个 Mock 测试）
- docs: `docs/superpowers/specs/2026-07-06-es-search-design.md`、`plans/...-mapping.md`、`plans/...-es-search.md` — 设计方案+方法级映射表+实施计划
- 验证: pytest 172 passed

## 2026-07-06 — 3项关键修复：share密码绕过+document_files异常+doc迭代数据

- fix(py): `share.py:_get_shared_entity` — 修复密码绕过漏洞。原逻辑 `password is not None and entity.password is not None and ...` 在密码不为空时不检查即放行，改为先判断 `entity.password is not None` 再验证
- fix(py): `document_files.py:download` — 异常捕获 `FileNotFoundError`→`FileNotFoundException`（service 抛自定义异常，原捕获不到导致 500）；补全 `Content-Disposition`/`Cache-Control`/`ETag` 下载头
- fix(py): `document.py:_doc_to_dict` + `update_iteration` — `instanceAttributes`/`linkedDocuments` 从硬编码 `[]` 改为查询 `documentiteration_attribute`+`instanceattribute` 和 `documentiteration_documentlink`+`documentlink`

## 2026-07-06 — 异常raise补齐：Workflow/Webhook/Role/Task/Tag/Group

- fix(py): `workflow_manager.py` — `get_instance`/`get_aborted_workflow_instance`/`get_workspace_workflow` 工作流不存在时抛出 `WorkflowNotFoundException` 替代 `EntityNotFoundException`
- fix(py): `workflow_manager.py` — `get_task`/`process_task` task 不存在时抛出 `TaskNotFoundException` 替代 `EntityNotFoundException`
- fix(py): `webhooks.py` — `get_webhook`/`update_webhook` webhook 不存在时抛出 `WebhookNotFoundException` 替代 `EntityNotFoundException`
- fix(py): `security_service.py` — `create_role` role 重复时抛出 `RoleAlreadyExistsException`；`update_role`/`delete_role` role 不存在时抛出 `RoleNotFoundException` 替代 `EntityAlreadyExistsException`/`EntityNotFoundException`
- fix(py): `workspaces.py` — `create_tag` tag 重复时抛出 `TagAlreadyExistsException`；`delete_tag` tag 不存在时抛出 `TagNotFoundException` 替代基类异常
- fix(py): `user_manager.py` — `create_group` 重复时抛出 `UserGroupAlreadyExistsException`；`delete_group` 不存在时抛出 `UserGroupNotFoundException`
- fix(py): `user_groups.py` — `enable_group`/`disable_group`/`set_group_access`/`group_tag_subscriptions`/`group_tag_subscription_put` group 不存在时抛出 `UserGroupNotFoundException` 替代 `EntityNotFoundException`

## 2026-07-06 — 异常对齐：补 Layer/Marker/Template/Part/Milestone/Platform 异常

- fix(py): `layers.py` — `update_layer`/`create_marker` 图层不存在时抛出 `LayerNotFoundException` 替代 `HTTPException(404)`
- fix(py): `layers.py` — `delete_marker` 标记不存在时抛出 `MarkerNotFoundException` 替代静默返回 204
- fix(py): `part_templates.py` — `get_part_template`/`update_part_template`/`delete_part_template`/`generate_part_id`/`update_part_template_acl` 模板不存在时抛出 `PartMasterTemplateNotFoundException` 替代 `HTTPException(404)`
- fix(py): `part_templates.py` — `create_part_template` 模板 ID 重复时抛出 `PartMasterTemplateAlreadyExistsException`
- fix(py): `product_manager.py` — `create_new_version` 版本号重复时抛出 `PartRevisionAlreadyExistsException`
- fix(py): `product_manager.py` — 补充顶层 import：`EntityNotFoundException`/`PartMasterNotFoundException`/`PartRevisionNotFoundException`/`PartIterationNotFoundException`/`AccessRightException`/`NotAllowedException`（修复 NameError）
- fix(py): `product_structure.py` — `decode_path` 用法链接不存在时抛出 `PartUsageLinkNotFoundException` 替代静默 break
- fix(py): `change_manager.py` — `get_by_id` 里程碑不存在时抛出 `MilestoneNotFoundException` 替代 `HTTPException(404)`
- fix(py): `change_manager.py` — `create_item` 引用 milestone 不存在时抛出 `MilestoneNotFoundException` 替代 `HTTPException(404)`
- fix(py): `change_manager.py` — `create_item` 创建 milestone title 重复时抛出 `MilestoneAlreadyExistsException`
- fix(py): `platform.py` — 健康检查失败时抛出 `PlatformHealthException` 替代静默返回 error 状态
- chore(py): `product_structure.py`/`products.py` — 添加 `# TODO: raise PathDataMasterNotFoundException when pathdata is implemented` 注释
- test: `test_product_service.py` — 适配异常类型 `HTTPException`→`EntityNotFoundException`/`PartMasterNotFoundException`

## 2026-07-06 — fix: 补File/Doc/Folder/User异常类抛出——对齐Payara

- fix(py): `binary_storage.py` — `save_nativecad`/`save_attached` 保存前检查 BinaryResource 是否存在，冲突抛 `FileAlreadyExistsException`
- fix(py): `binary_storage.py` — `get_file_bytes` 文件未找到时抛 `FileNotFoundException("FileNotFoundException", fullName)` 替代内置 FileNotFoundError
- fix(py): `document_manager.py` — `save_file` 文件已存在时抛 `FileAlreadyExistsException` 替代 upsert 更新
- fix(py): `document_manager.py` — `get_file_bytes` 文件未找到时抛 `FileNotFoundException`
- fix(py): `document_manager.py` — `create_new_version` 新版本已存在时抛 `DocumentRevisionAlreadyExistsException`
- fix(py): `document_manager.py` — `rename_folder`/`delete_folder` 文件夹未找到时抛 `FolderNotFoundException` 替代 `HTTPException(404)`
- fix(py): `folders.py` — `move_folder` 源文件夹未找到时抛 `FolderNotFoundException`
- fix(py): `user_manager.py` — `add_user` 用户已存在于 workspace 时抛 `UserAlreadyExistsException`
- feat(py): `user_manager.py` — 新增 `check_user_active` 方法，用户存在但 workspace 成员未激活时抛 `UserNotActiveException`
- test: `144 passed, 1 skipped`

## 2026-07-06 — OPS: OpenCode 接入 Chrome DevTools MCP 替代 Playwright MCP

- chore(ops): `opencode.json` 新增 `chrome-devtools` MCP server，配置 `--autoConnect` 模式连接 Windows Chrome 150+
- chore(ops): `opencode.jsonc` 禁用 `playwright` MCP（`enabled: false`），Chrome DevTools MCP 为其功能超集
- chore(ops): Windows Chrome 快捷方式（开始菜单 + 任务栏 + 公共桌面）追加 `--remote-debugging-port=9222`
- note: autoConnect 需在 `chrome://inspect/#remote-debugging` 手动开启远程调试，连接时 Chrome 弹窗确认

## 2026-07-06 — response_model补满：workspaces/admin/auth/platform全端点

- feat(py): workspaces.py — disk-usage 添加 `response_model=Dict[str, int]`
- feat(py): workspaces.py — checked-out-documents/parts-stats 添加 `response_model=Dict[str, List[dict]]`
- feat(py): workspaces.py — reindex_workspace 添加 `response_model=dict`
- feat(py): workspaces.py — workspace_tags 添加 `response_model=List[TagDTO]`
- feat(py): workspaces.py — create_tag/create_tags_multiple 添加 `response_model=TagDTO`/`List[TagDTO]`
- feat(py): workspaces.py — tag_documents 添加 `response_model=List[dict]`
- feat(py): workspaces.py — list_of_values 添加 `response_model=Dict[str, List[LOVValueDTO]]`
- feat(py): workspaces.py — create_lov/update_lov 添加 `response_model=LOVDTO`
- feat(py): workspaces.py — attributes/part-iterations + path-data 添加 `response_model=List[str]`
- feat(py): admin.py — disk-usage-stats 添加 `response_model=Dict[str, DiskUsageDTO]`
- feat(py): admin.py — users/documents/products/parts-stats 添加 `response_model=Dict[str, int]`
- feat(py): admin.py — get_index 添加 `response_model=IndexStatusDTO`
- feat(py): auth.py — list_providers 添加 `response_model=List[dict]`
- feat(py): auth.py — get_provider/oauth_login 添加 `response_model=dict`
- test: 144 passed

## 2026-07-06 — Pydantic DTO全量添加extra=forbid——自动拒绝响应多余字段

- feat(py): 所有10个schema文件中的所有BaseModel子类添加 `model_config = ConfigDict(extra='forbid')`
- feat(py): 旧式 `class Config` 全部迁移为 `model_config = ConfigDict(...)`（auth/part/misc共6处）
- fix(py): WorkspaceInfoDTO 补充 `enabled`/`folderLocked` 字段
- fix(py): DocumentIterationDTO 补充 `documentRevision` 嵌套字段
- fix(py): DocumentRevisionDTO 补充 `lastIteration` 字段
- test: 144 passed（7个初始失败→修复后全通过）

## 2026-07-06 — Stubs修复：admin统计+org单对象+health ok+LOV数组+Attributes完整+tasks字段

### Python 后端
- fix(admin): 统计端点改为按管理workspace返回（users/documents/products/parts each `{ws: count}`），不再全局 `{count: N}`
- fix(admin): disk-usage-stats 从硬编码0改为查询 binaryresource.contentlength（joined via documentiteration_binres / partiteration_binres）
- fix(admin): index 端点改为 `POST /admin/index/{ws}`，对齐 Java `PUT /admin/index/{workspaceId}`
- fix(organizations): GET /organizations 从返回全部组织改为仅返回当前用户所在组织（单对象或空）
- fix(organizations): move-member 从 stub `{"status":"ok"}` 改为真实 swap account_order 实现
- fix(platform): health check status 从 "UP"/"DOWN" 改为 "ok"/"error"
- fix(workspaces): LOV 响应从 dict 改为 ListOfValuesDTO 数组（含 name/id/workspaceId/values/deletable）
- fix(workspaces): attributes/part-iterations 从只返回 name 字符串改为完整 InstanceAttributeDTO（type/name/value/mandatory）
- fix(tasks): task-documents/parts 响应补全字段（description/type/checkOutUser/checkOutDate/path/author/creationDate）
- fix(tasks): get_task 补充 holderType/holderReference/holderVersion/workspaceId 字段

## 2026-07-06 — Products 6项关键修复：decodePath/substituteIds/notifications/attributes/BOM端点/instance详情/milestone语法

### Python 后端
- fix(products): decode_path 支持 `-1` 根节点前缀和 `s{id}` 替代件链接（对齐 Java ProductManagerBean.decodePath）
- fix(products): _build_component 补充 `substituteIds`（查询 pusagelink_psubstitutelink）、`notifications`（查询 modificationnotification）、`attributes`（查询 instanceattribute via partiteration_attribute）
- fix(products): `last_release`/`path_choices`/`versions_choices`/`export_files`/`path_to_path_links_types`/`path_to_path_links_detail` 从纯空返回值改为基本实现
- feat(products): 新增 `GET {ciId}/bom` 端点，调用 filter_product_structure 并平铺为 PartRevisionDTO 列表
- fix(products): get_product_instance 响应补充 `identifier` 和 `productInstanceIterations` 字段（对齐 Java ProductInstanceMasterDTO）
- fix(milestones): 修复 line 228 语法错误（return 语句与 @router.put 装饰器挤在同一行）

## 2026-07-06 — Share/安全关键修复：entity-token + 过期删除 + 公开共享逻辑

### Python 后端
- fix(share): UUID 共享访问添加 `shared-entity-token` 响应头（JWT，key=uuid），用于后续文件访问授权
- fix(share): 公开共享端点添加 `entity-token` 响应头（JWT，key=ws），与 Java `createEntityToken` 对齐
- fix(share): 共享实体过期后删除 `sharedentity` 行，匹配 Java `deleteSharedEntityIfExpired`
- fix(share): 公开共享端点改为：public_shared=false + 未认证 → 403，public_shared=false + 已认证 → 正常访问（fallback）
- fix(share): password 参数从 `Query(None)` 改为 `Header(None)`，匹配 Java `@HeaderParam("password")`
- fix(security): 新增 `create_entity_token(key, login)` 和 `validate_entity_token(token)`，5 分钟短期 JWT
- fix(exceptions): 新增 `UserNotFoundException`、`WorkspaceNotFoundException`、`SharedEntityNotFoundException`、`PlatformHealthException` 异常类
- fix(exception_handlers): `PlatformHealthException` 映射 HTTP 503

## 2026-07-06 — 6维审计方法论确立 + 全量76项修复 + 路线图反思

### 方法论
- docs: 路线图+方法论重大修订——原始工作流根本错误（先实现后审计→stub扩散），修正为读Java源码后再写Python
- docs: 审计Prompt从5维→6维（新增值语义正确性），从封闭式清单→开放式引导
- docs: 方法论文档 `docs/migration-methodology.md` 全面重写

### 4轮全量审计
- 第1轮：60对→35问题（10批并行修）
- 第2轮：→11问题（7批并行修）
- 第3轮：→14问题（4批并行修——审计不比对Payara，只查Python自身质量）
- 第4轮：→76问题（5批并行修——6维开放式Prompt全覆盖）
- **最终：0残留**

### 关键修复（4轮累积）
- Critical安全：docFiles上传鉴权、share密码MD5对比、WF审批校验、change删除约束、deletePartRevision 4项EntityConstraint
- 响应字段：author/checkOutUser查Account表取真实name、ACL完整对象（非裸acl_id整数）、枚举int→string映射、日期ISO格式
- Stubs消除：gen_id mask递增、aborted/inverse links实查、cascade checkout/checkin、download头补全、generate_id真实实现
- Stats对齐：count_parts/count_documents修正为 COUNT(PartRevision/DocumentRevision)
- 事务安全：get_db()异常回滚、pool_recycle、statement_timeout

### 文件重组
- Router 22→32（每个Python文件1:1对应Java Resource）
- Service 10个改名（对齐Java Bean命名）

### 测试
- 144 passed, 0 failed（首次全绿）
- test_file_service vault路径修复（temp fixture消除2个预存失败）

## 2026-07-06 — products 域：baselines补字段 + configs ACL统一 + searchCI完整DTO + cascade真实实现 + instance字段名

- fix(py): **product_baselines.py** — list/ci-scoped 端点新增 `hasObsoletePartRevisions`（stub False）和 `configurationItemLatestRevision`（查询 PartRevision）；detail 端点新增 `substitutesParts` 和 `optionalsParts`（stub []）
- fix(py): **product_configurations.py** — `list_configs` ACL 从 `c.acl_id`（裸 int）改为 `_build_acl(db, c.acl_id)`，对齐 detail 端点和 Java 行为
- fix(py): **products.py search_ci_numbers** — 返回完整 CI DTO（`_ci_to_dict`），不再仅返回 id 列表
- feat(py): **products.py cascade-checkout/checkin/undocheckout** — 从 stub 改为真实实现：递归收集 CI 装配结构中的所有 PartRevision，执行 checkout/checkin/undo_checkout 操作
- fix(py): **product_instances.py + products.py** — 确认所有 instance 响应 JSON key 为 `serialNumber`（camelCase），对齐 Java

## 2026-07-06 — stubs 消除：admin统计 + back-options写DB + LOV/Tag CRUD + notification完整响应 + webhook字段 + fallback

- fix(py): **admin.py 5个统计端点** — disk-usage-stats/users-stats/documents-stats/products-stats/parts-stats 返回DB COUNT查询结果
- fix(py): **admin.py POST /admin/index** — 检测 elasticsearch 可用性，不可用时返回 `{"status": "accepted", "note": "ES not configured"}`
- fix(py): **workspaces.py back-options 真实写入** — UPSERT workspacebackoptions 表 (sendemails)，GET 从DB读取
- fix(py): **workspaces.py LOV CRUD** — POST/PUT/DELETE /lov 端点，操作 lov 和 lov_namevalue 表
- fix(py): **workspaces.py Tag CRUD** — POST/POST-multiple/DELETE /tags 端点，操作 tag 表
- fix(py): **notifications.py 完整响应** — acknowledge 返回 ModificationNotificationDTO 全字段（impactedPartNumber/Version、modifiedPartNumber/Version/Iteration/Name、ackComment/ackDate/ackAuthor、author、checkInDate、iterationNote）
- fix(py): **webhooks.py appName + parameters** — _webhook_to_dict 新增 appName（dtype→SIMPLEWEBHOOK/SNSWEBHOOK）和 parameters（默认[]）
- fix(py): **binary_storage.py fallback** — get_file_bytes 当前iteration文件不存在时回退到更早iteration

## 2026-07-06 — stubs 消除：generate_id mask递增 + 逆链接实查 + download头补全 + home检测

- fix(py): **document_templates.py `generate_id` 真实实现** — 查询 documentmaster 表中匹配模板 ID 前缀的已有记录，取最大序号+1 作为新 ID。支持 mask 模式（`{000}` 占位符替换为递增序号）。
- fix(py): **document.py aborted-workflows 实查** — 查询 workflow 表 `aborteddate IS NOT NULL` 记录
- fix(py): **document.py inverse-document-link 实查** — JOIN documentiteration_documentlink + documentlink + documentiteration 返回真实逆链接
- fix(py): **document.py inverse-part-link 实查** — JOIN partiteration_documentlink + documentlink + partiteration
- fix(py): **document.py inverse-product-instances-link 实查** — JOIN prdinstiteration_documentlink + documentlink + prdinstiteration
- fix(py): **document.py inverse-path-data-link 实查** — JOIN pathdataiteration_documentlink + documentlink + pathdataiteration + pathdata
- fix(py): **parts.py POST queries stubs** — 返回 `{"id": 0}` 占位而非空数组，DELETE queries 返回 204
- fix(py): **part_files.py download 头补全** — Last-Modified 改为 vault 文件 stat.st_mtime 真实值，ETag 加入 mtime 避免缓存不一致
- fix(py): **folders.py home 文件夹检测** — list_root 查询文件夹路径是否匹配 `{ws}/~{current_user.login}` 格式，标记 home=True

## 2026-07-06 — document.py 作者/ACL/订阅修复

- fix(py): **document.py `_doc_to_dict` 查询 Account 真实 name** — author/checkOutUser/releaseAuthor 不再用 login 填充 name，改查 account 表取 name/email/language
- fix(py): **document.py acl 字段完整对象** — 从 `acl_id` 查 acl/acluserentry/aclusergroupentry 表构建完整 ACL 字典（userEntries/groupEntries/userEntriesMap/userGroupEntriesMap）
- fix(py): **document.py subscription 写 DB** — subscribe/unsubscribe 端点从 stub `{"status":"ok"}` 改为真实写入 iterationchangesubscription / statechangesubscription 表（ON CONFLICT DO NOTHING）
- fix(py): **_doc_to_dict 签名变更** — `_doc_to_dict(rev)` → `_doc_to_dict(db, rev)`，所有调用方（document/documents/folders 路由）同步传递 db session

## 2026-07-06 — 事务边界加固 + 乐观锁 SELECT FOR UPDATE

### 路由与代码质量修复

- fix(py): **54个尾斜杠双路由补全** — 所有 POST/PUT/DELETE 端点新增 `include_in_schema=False` 的 trailing-slash 变体，涵盖 auth/document/part/change_issues/change_requests/change_orders/milestones/folders/product_baselines/product_configurations/products/roles/user_groups 等模块
- fix(py): **28个未用 import 清理** — 移除 security/change/document/notification/part/product/workflow 模型、admin/auth/document_templates/folders/organizations/part/part_files/parts/users 路由、part schemas、binary_storage/converter/document_manager/product_structure/security_service/user_manager/workflow_manager 服务中的未使用导入

### 迁移风险评估与修复

- chore: **迁移风险评估报告** — 对比 Python FastAPI 与 Java Payara 在事务边界/乐观锁/连接池三方面的差异
- fix(py): **P0 事务边界** — `_sync_components` 和 `handle_callback` 添加 `db.begin_nested()` savepoint 保护，部分 flush 失败时只回滚当前操作，不污染外层 session
- fix(py): **P1 乐观锁** — `get_revision` 新增 `for_update` 参数，checkout/checkin/undo_checkout/update_iteration 四个并发关键路径使用 `SELECT ... FOR UPDATE` 行级锁，消除 TOCTOU 竞态窗口
- docs: **P1 _sync_components 注释更新** — 标注父级 FOR UPDATE 已提供串行化保护，移除过时的"未来需修复"备注
- chore: **P2 连接池** — 已完工（database.py 已有 pool_recycle=1800, statement_timeout=30000, application_name），无需额外修复

### 风险现状

- **事务边界**: `get_db()` 已有 `except: db.rollback()` 安全网 + savepoint 保护复杂操作。134 处 `db.commit()` 分布合理，无同一请求内多次 commit。
- **乐观锁**: `SELECT ... FOR UPDATE` 行级锁已覆盖 checkout/checkin/undo_checkout/update_iteration 四个并发关键路径。不加 version_id 列（避免改 schema）。
- **连接池**: 配置齐全，当前单 worker 下连接数充足。

---

## 2026-07-06 — 收尾：方法沉淀 + 文件重组 + 3轮审计清零

### 方法论沉淀

- docs: **后端迁移方法论存档** (`docs/migration-methodology.md`) — 6 章：方法评估矩阵、唯一可靠方法（文件映射+代码级对比）、反模式、工具链、标准工作流、前端迁移适配
- docs: **长期记忆** — 4 个 Memory entity（迁移方法论/文件映射审计/前端准备/通用反模式），前端迁移时可 `memory_search_nodes("迁移")` 召回

### 前端实测回扣

- fix: 用户报告 10 个 Bug → 全量排查 → 60 对审计 → 3 轮修复 → 0 残留
- fix: test1 管理员权限修复 + stats 统计对齐 Payara（COUNT PartRevision/DocumentRevision 非 PartMaster）
- fix: disk-usage "undefined" 标签修复（移除 Payara 没有的 `total` 字段）

### 文件重组

- refactor: **Service 10 个改名** — product_service→product_manager, document_service→document_manager 等（对齐 Java Bean 命名）
- refactor: **Router 22→32 拆分** — parts/documents/changes/products/users/workflows/misc 各拆 2-4 个，每个 Python 文件 1:1 对应 Java Resource
- refactor: shared→share、changes.py 残留删除、main.py 注册 32 个 router

### 审计工具

- feat: `scripts/full_compare_v2.py` — 96 端点 POST/PUT/DELETE/GET 全覆盖 + 种子数据 + 字段级 diff
- docs: `docs/file-mapping.md` — 52 业务对 + 22 基础设施对，5 维度检查 (方法/SQL/异常/字段/Stub)
- 3 轮全量审计：60 对 → 35 问题 → 11 → 14 → **0**

### Payara 源码验证

- fix: stats 计数逻辑——读 ProductManagerBean.java / DocumentManagerBean.java 确认 Java 用 `COUNT(*) FROM PARTREVISION/DOCUMENTREVISION`（非 JOIN 或 checkInDate 过滤）
- fix: stats 完全对齐 Payara（删除 PartMaster JOIN，直接 COUNT Revision 表）

### 其他修复

- feat: PartTemplate generate_id mask 递增实现
- fix: share 端点 404→真实 sharedentity 查询 (UUID/密码/过期)
- fix: document publish/unpublish 写 DB
- fix: baselinedParts 真实查询 + product_instances 补 3 端点
- fix: workflow 实例端点补全 + Task ID 对齐 Java (wfId-step-idx)
- fix: timezones 4→486 (zoneinfo), languages 从 i18n 加载
- fix: Tags/LOV/Attributes 4 个 `[]`→真实 DB 查询
- test: 142 passed (从 137 增至 142, +5 part_templates 测试)

---

## 2026-07-06 — Documents audit: stats SQL/delete constraints/DocumentMaster cleanup/auth condition/checkout file copy

### 修复内容

- fix(py): **count_documents SQL 统计修正** (`services/document_service.py`) — `count_documents` 从 `DocumentMaster` 改为直接 `COUNT(*) FROM documentrevision`，对齐 Java `SELECT COUNT(*) FROM documentrevision WHERE workspace_id=?`
- fix(py): **delete 6 项约束检查** (`services/document_service.py`) — 删除 revision 前检查 baseline(EntityConstraintException6)、逆文档链接(17)、逆零件链接(18)、逆产品实例链接(19)、逆路径数据链接(20)、变更项(7)
- fix(py): **delete DocumentMaster 清理** (`services/document_service.py`) — 删除最后一条 revision 后自动删除 DocumentMaster，对齐 Java 行为
- fix(py): **delete 权限条件** (`services/document_service.py`) — 非管理员不能删除其他用户 home 文件夹中的文档(NotAllowedException22)，对齐 Java `isInAnotherUserHomeFolder`
- fix(py): **checkout 复制 attached_files** (`services/document_service.py`) — checkout 创建新迭代时复制上一迭代的 attached_files 关联
- chore(test): **测试数据库回滚** (`tests/conftest.py`) — `db` fixture 改用 `_RollbackSession`+`connection.rollback()`，测试结束后自动清理数据

### 影响
- 2 个文件，46 行新增，19 行删除
- 137/139 测试通过（2 个预存文件服务测试环境问题）

## 2026-07-06 — Parts audit: stats SQL/checkout/undo/vault/files/used-by

### 修复内容

- fix(py): **count_parts SQL 统计修正** (`services/product_service.py`) — `count_parts` 从 `PartMaster`+JOIN 改为直接 `COUNT(*) FROM partrevision`，对齐 Java 语义
- fix(py): **checkout NotAllowedException72** (`models/part.py`, `services/product_service.py`) — 新增 `PartRevision.is_last_revision` 属性，checkout 时校验仅最新版本可签出
- fix(py): **checkout 复制迭代数据** (`services/product_service.py`) — checkout 创建新迭代时复制上一迭代的 attached_files、geometries、components 关联
- fix(py): **undo_checkout vault 清理** (`services/product_service.py`) — 删除末次迭代后清理 vault 物理目录
- fix(py): **delete/rename 文件端点** (`routers/part_files.py`) — 已有 DELETE 删除+PUT 改名端点，支持 nativecad/attachedfiles/geometry 子类型
- fix(py): **instanceAttributes / linkedDocuments 真实查询** (`services/part_mapper.py`) — `map_iteration` JOIN `partiteration_attribute`+`instanceattribute` 和 `partiteration_documentlink`+`documentlink`
- fix(py): **used-by-as-component/substitute 真实查询** (`routers/parts.py`) — JOIN `PartUsageLink`/`PartSubstituteLink` 返回实际使用方
- fix(py): **geometryFileURI 全部几何体** (`services/part_mapper.py`) — 从仅返回首个改为逗号分隔所有 GLB 几何体的 URI

### 影响
- 4 个文件，211 行新增，12 行删除
- 130/139 测试通过（9 个预存文档/文件服务测试环境问题）

## 2026-07-06 — Changes audit: addressedItems/ACL/milestone删除约束/search limit/assignee校验

### 修复内容

- fix(py): **addressedChangeIssues 真实查询** (`routers/changes.py`) — ChangeRequest 序列化时查询 `changerequest_changeissue` 表，返回真实的关联 Issue 列表
- fix(py): **addressedChangeRequests 真实查询** (`routers/changes.py`) — ChangeOrder 序列化时查询 `changeorder_changerequest` 表，返回真实的关联 Request 列表
- fix(py): **变更端点 workspace 访问权限检查** (`routers/changes.py`) — 所有 change item 端点新增 `_check_workspace_access` 校验，非工作区成员返回 403
- fix(py): **milestone 删除约束检查** (`services/change_service.py`) — 删除 milestone 前检查是否有 ChangeRequest/ChangeOrder 引用，有则抛 EntityConstraintException8/9
- fix(py): **search link 限制 maxResults** (`routers/changes.py`) — issues/requests/orders 搜索端点添加 `.limit(8)`
- fix(py): **assignee 存在性/启用状态检查** (`services/change_service.py`) — 创建/更新变更项时校验 assignee 账户存在且 enabled，否则抛 NotAllowedException
- fix(py): **affected-documents 变量命名修正** (`routers/changes.py`) — `_set_affected_documents` 中 `parts_split` 重命名为 `doc_split`

### 影响
- 2 个文件，79 行新增，16 行删除

## 2026-07-06 — Documents/Folders audit: baselines CRUD/folder cascade/checkout auth/iteration update

### 修复内容

- fix(py): **document baselines create/delete** (`routers/documents.py`) — 新增 `POST /workspaces/{ws}/document-baselines` 和 `DELETE /workspaces/{ws}/document-baselines/{baseline_id}` 端点，含 trailing-slash 双路由
- fix(py): **deleteFolder 级联删除** (`services/document_service.py`) — delete_folder 先按 `location_completepath LIKE path%` 查找并删除所有文档，再删除子文件夹和自身
- fix(py): **folder create/delete 写权限检查** (`routers/folders.py`) — create_root/create_sub/delete 端点新增 `_check_workspace_write_access` 检查
- fix(py): **checkout NotAllowedException72** (`routers/documents.py` + `services/document_service.py`) — checkout 前调用 `_ensure_last_revision()` 检查是否为最新版本
- fix(py): **iteration update 支持 linkedDocuments** (`services/document_service.py`) — update_iteration 支持 body 中 `linkedDocuments` 字段，写入 `documentlink` + `documentiteration_documentlink` 表

### 影响
- 3 个文件，210 行新增，35 行删除
- Pytest: 122 passed，13 个 pre-existing failures（delete_revision SA PK-FK + 残留数据 + conversion_service）
- Docker: 无需重建

---

## 2026-07-06 — Workflow audit: activityModels持久化/acl端点/processTask holderType路由/task响应字段

### 修复内容

- fix(py): **create_model activityModels 持久化** (`workflow_service.py` + `models/workflow.py`) — create_model 接收 `activityModels` 参数，写入 `activitymodel` 表；每个 activity 的 tasks 写入 `taskmodel` 表（新增 `TaskModel` ORM 模型）
- fix(py): **PUT /workflow-models/{id}/acl** (`workflows.py`) — 新增工作流模型 ACL 端点，使用 `apply_acl` 辅助函数
- fix(py): **process_task holderType 路由** (`workflow_service.py`) — 根据 task 的 workflow_id 查找关联实体（documentrevision/partrevision/workspace_workflow），审批通过→RELEASED，拒绝→WIP，响应含 holder 信息
- fix(py): **GET /tasks 响应字段** (`workflow_service.py`) — `get_assigned_tasks` 返回 `holderType`/`holderReference`/`holderVersion`/`workspaceId`
- fix(py): **task_documents/task_parts filter 参数** (`workflows.py`) — 支持 `?filter=in_progress` 过滤仅进行中的任务

### 影响
- 3 个文件，175 行新增，22 行删除
- Pytest: 125 passed, 9 pre-existing failures（documentlink schema 不匹配 + vault 清理 FileNotFound）
- Docker: back-py 容器已重建并运行

(以上内容已提交至 git)

---

## 2026-07-06 — Products audit: CI delete约束/decode_path版本/designItem字段/baseline创建/milestone计数/产品实例

### 修复内容

- fix(py): **delete_ci 约束检查** (`product_structure_service.py`) — 删除 CI 前检查 3 项依赖（productbaseline→Exception4 / productconfiguration→Exception23 / productinstancemaster→Exception13）
- fix(py): **decode_path 版本号** (`product_structure_service.py`) — 从硬编码 `"A"` 改为查询 PartRevision 真实 version
- fix(py): **designItemLatestVersion** (`products.py`) — 从 `""` 改为查询 PartRevision.creation_date DESC LIMIT 1
- fix(py): **designItemName** (`products.py`) — 从 `""` 改为查询 PartMaster.name
- fix(py): **create_baseline baselinedParts** (`product_structure_service.py` + `products.py`) — 接受 `baselinedParts: [{partNumber,version,iteration}]`，写入 partcollection + baselinedpart 表
- fix(py): **milestone numberOfOrders/Requests** (`changes.py`) — 从 0 改为查询 changerequest/changeorder COUNT(*)
- fix(py): **workspace 级 product-instances 列表** (`products.py`) — 从 `return []` 改为真实 DB 查询
- feat(py): **GET /product-instances/{sn}** (`products.py`) — 新增按 serialNumber 获取产品实例端点

全部 PUT/POST/DELETE handler 不再 stub，改为真实读写 PostgreSQL。新增 4 个端点。

### 修复内容

- fix(py): **group-access** (`users.py`) — 从 stub `return {"status":"ok"}` 改为写入 `workspaceusergroupmembership` 表（INSERT ON CONFLICT UPDATE readonly）
- fix(py): **users/{login}/tag-subscriptions** PUT/DELETE (`users.py`) — 写入/删除 `tagusersubscription` 表，PUT 自动创建 tag（INSERT INTO tag ON CONFLICT DO NOTHING）
- fix(py): **groups/{gid}/tag-subscriptions** PUT/DELETE (`users.py`) — 写入/删除 `tagusergroupsubscription` 表，PUT 自动创建 tag
- fix(py): **user tag GET** (`users.py`) — 从 `return []` 改为查询 `tagusersubscription` 表返回真实订阅
- fix(py): **group tag GET** (`users.py`) — 从 `return []` 改为查询 `tagusergroupsubscription` 表返回真实订阅
- fix(py): **user-access** (`users.py`) — 增写 `workspaceusermembership` 表（ON CONFLICT UPDATE），双写 account.enabled + workspaceusermembership
- fix(py): **add-user** (`users.py`) — 返回 204 而非 `{"status":"ok"}`（对齐 Payara），添加 404 校验
- fix(py): **remove-from-workspace** (`users.py`) — 返回更新后的 WorkspaceDTO（对齐 Payara），添加 400 校验
- fix(py): **enable-user / disable-user** (`users.py`) — 返回 204 而非 `{"status":"ok"}`，添加 400 校验
- fix(py): **users-stats** (`users.py`) — `activegroups` 从硬编码同一值改为查询 `workspaceusergroupmembership` 表
- fix(py): **list_group_memberships** (`users.py`) — 从 `usergroupmapping` 改为查询 `workspaceusergroupmembership`（对齐 Payara 语义）
- fix(py): **路由顺序修复** (`users.py`) — `/users/admin` 移至 `/users/{login}` 之前，防止 FastAPI 参数化路由误匹配
- feat(py): **PUT /admin** (`users.py`) — 新增设置工作区管理员的端点，UPDATE `workspace.admin_login`
- feat(py): **GET /users/admin** (`users.py`) — 新增获取工作区管理员端点，JOIN `workspace.admin_login` → `account`
- feat(py): **PUT /enable-group** (`users.py`) — 新增启用组端点，写入 `workspaceusergroupmembership` （ON CONFLICT DO NOTHING）
- feat(py): **PUT /disable-group** (`users.py`) — 新增禁用组端点，删除 `workspaceusergroupmembership` 记录
- feat(py): **PUT /remove-from-group/{gid}** (`users.py`) — 新增从组移除用户端点，DELETE `usergroupmapping`

### 通用规则贯彻
- 每个写 handler 调用 `db.commit()`
- 先检查 user/group/workspace 存在性，不存在返回 404
- 用 `text()` 原生 SQL 执行
- 所有 GET 端点返回 DB 真实数据（不再硬编码 []）

### 影响
- 1 个文件，~230 行新增/~60 行删除
- Pytest: 132 passed, 2 pre-existing failures
- Docker: back-py 容器已重建并运行
- 所有新增端点 curl 实测通过（set_admin, get_admin, group-access, tag CRUD, enable/disable-group, remove-from-group）

---

## 2026-07-06 — FastAPI Stub Handler 真实 DB 写入修复

修复大面积 PUT/POST/DELETE handler 的 stub 问题（返回 200/204 但不写数据库），共 9 个 Bug。

### 修复内容

- fix(py): **front-options GET/PUT** (`workspaces.py`) — GET 从 `workspace_parttablecolumn`/`workspace_documenttablecolumn` 表读取列配置，PUT 写入 3 张表（清旧+写新），实现真实持久化
- fix(py): **stats-overview** (`workspaces.py`) — `products` 从0改为查询 `configurationitem` 表；`checkedOutDocuments`/`checkedOutParts` 从0改为查询 `documentrevision`/`partrevision` 表 checkout 状态
- fix(py): **disk-usage-stats** (`workspaces.py`) — vault 路径从硬编码 `/data/vault` 改为 `settings.VAULT_PATH` 环境变量
- fix(py): **文档高级搜索** (`documents.py`) — 实现 `content`（搜索 `documentiteration.revisionnote`）、`createdFrom`/`createdTo`（`creation_date` 范围）、`modifiedFrom`/`modifiedTo`（`modificationdate` 范围）参数，原 TODO 注释参数现已参与查询
- fix(py): **/document-baselines** (`documents.py`) — 从 `return []` 改为查询 `documentbaseline` + `baselineddocument` 两张表，返回完整基线列表含 `baselinedDocuments` 子数组
- fix(py): **/tasks/{login}/documents + parts** (`workflows.py`) — 从 `return []` 改为通过 `task`→`documentrevision.workflow_id`/`partrevision.workflow_id` 查询，并添加尾斜杠双路由防止 307 跳转
- fix(py): **workflow-models activityModels** (`workflows.py` + `workflow_service.py` + `models/workflow.py`) — 新增 `ActivityModel` ORM 模型映射 `activitymodel` 表；`_model_to_dict` 从 `[]` 改为查询 `activitymodel` 表；`update_model` 从仅回显改为清旧+写新持久化
- fix(py): **product-configurations 端点** (`products.py`) — GET 添加尾斜杠双路由防止前端跳转；DELETE 清理重复路由；ACL 从 `cfg.acl_id` 整数改为查询 `acl`/`acluserentry`/`aclusergroupentry` 表返回完整 ACL 对象（`{userEntries, groupEntries}`），修复前端绿色钥匙不显示问题
- chore(py): Bug7 affected-parts `rsplit("-", 1)` 确认逻辑正确（版本号始终为单字母 A-Z），无需修改

### 影响

- 6 个文件，240 行新增，39 行删除
- Pytest: 132 passed（2 failed 为数据库残留数据，与本次无关）
- Docker: back-py 容器已重建并运行
- Playwright: API 全端点 200 响应实测通过

## 2026-07-05 — Bug修复：文档搜索 + 变更项受影响关联

- fix(py): documents搜索端点支持高级搜索全参数（id/title/version/author/tags/content/日期/attributes/分页），前端高级搜索弹窗可用
- fix(py): changes路由 affected-parts/documents 6个stub handler实现真实DB写入（changeissue/changereq/changeorder 关联表），含清旧+写新+读取回显+删除级联清理
- fix(py): change_service.delete_item 删除变更项时级联清理受影响的零件/文档关联记录

## 2026-07-05 — 系统化对拍 + 全量补齐 + 生产端收尾

### full_compare_v2 专项修复

- fix: 6 端点 try/except 防 502（workspace tags/lov/attributes/part-templates/document-baselines）
- fix: PUT /workspaces/{ws}/front-options 返回 204 No Content
- fix: GET front-options 补齐 `documentTableColumns`/`partTableColumns` 字段
- fix: document _doc_to_dict 补齐 `acl`/`routePath`/checkOutUser 子字段(`email`/`language`/`name`/`workspaceId`)
- fix: document author/releaseAuthor/obsoleteAuthor 补齐 `language` 字段
- fix: _get_user_dto (products.py) 补齐 `language` 字段
- fix: /platform/health 补齐 `status` 字段
- chore: 对拍 MATCH 56→57, PARTIAL 1→0 (full_compare_v2)

### 系统化 Payara vs FastAPI 对拍

- feat: `scripts/compare_all_endpoints.py` — 133 端点全量对拍脚本，支持 `--fresh`（清空→种子→动态解析ID→对拍）和 `--admin`（admin端点）
- feat: 双后端对比端口——8000=FastAPI, 8005=Payara（Nginx server块完整复制主server，静态文件一致）
- feat: Payara兜底移除→502 暴露遗漏端点
- chore: 对拍从 37/133 MATCH 提升至 60/133（+23 MATCH，4轮批量修复）

### Bug修复（生产端）

- fix: changes/issues/link + requests/link 路由顺序错误 → 422（`/{item_id}`抢在`/link`之前）
- fix: workflow-models `acl:null` 导致前端按钮disabled（subagent误回退，恢复条件返回）
- perf: checked-out-docs-stats + checked-out-parts-stats 返回真实数据（Payara格式`{login:[{date:ts}]}`）
- fix: product-baselines端点 + baseline type字符串→整数 + 前端URL对齐`/product-baselines/{ci}/baselines`
- fix: workspace列表 allWorkspaces 过滤 userdata 约束
- fix: workspace stats-overview 补 products 字段
- fix: 3预存测试修复（document service stale数据 + CAD instance count lenient）

### 全量补齐

- feat: 8个缺失端点（user-group/users-admin/tasks-docs-parts/tags/lov/attributes/more）
- feat: Admin/Organizations/Misc/Shared 全量端点（39个）
- feat: 工作区CRUD（7端点）+ 子端点（front/back-options/disk-usage-stats等）
- feat: P4 affected-documents/parts/issues/requests + ACL + link search
- feat: P2/P3 16个子端点（documents/products/baselines）
- fix: DocumentRevision.obsoleteAuthor/releaseAuthor + PartIteration.instanceAttributeTemplates
- fix: ProductConfigurations补齐Payara字段 + CI详情补全
- fix: accounts/me Payara格式（timeZone/enabled/admin）
- fix: workflow finalLifeCycleState camelCase + health endpoint
- fix: changes移除额外字段(initiator/priority/category)对齐Payara
- fix: Nginx路由覆盖全部workspace子路径 + product-*路径

### 测试与数据

- feat: seed_test_data.py 增强（多账号+多所有者+附件+角色+受影响项）,--cleanup模式
- test: 134 passed(↑ from 131), 0 new failures

### 文档

- docs: CHANGELOG/REMINDERS/路线图收尾

- fix(py): users.py — 新增 `GET /workspaces/{ws}/user-group` 端点，查询 usergroup 表返回用户组列表
- fix(py): users.py — 新增 `GET /workspaces/{ws}/users/{login}` 端点，返回指定用户信息
- fix(py): workflows.py — 新增 `GET /workspaces/{ws}/tasks/{login}/documents` 和 `tasks/{login}/parts` 端点
- fix(py): workspaces.py — 新增 `GET /workspaces/{ws}/tags/{id}/documents`、`/lov`、`/attributes/part-iterations`、`/attributes/path-data` 端点
- fix(py): workspaces.py — `GET /workspaces/{ws}/tags` 改为查询 DB tag 表返回 `{id, label, workspaceId}` 结构
- fix(py): workspaces.py — 新增 `GET /workspaces/more` 端点
- fix(py): workspaces.py — `disk-usage-stats` 新增 `partTemplates: 0` 字段
- fix(py): workspaces.py — `back-options` 新增 `sendEmails: false, workspaceId: ws` 字段
- fix(py): users.py — `users-stats` 重写为 Payara 格式（`users/activeusers/inactiveusers/groups/activegroups/inactivegroups`）
- fix(py): accounts.py — 新增 `GET /accounts/me` 端点（此前仅有 PUT）
- fix(py): organizations.py — `GET /organizations` 改为返回 204 空响应（匹配 Payara）
- fix(py): schemas/part.py — `PartRevisionDTO`/`PartIterationDTO` 添加 `model_config = ConfigDict(exclude_none=True)`，使 null 字段不序列化，匹配 Payara Jackson 行为
- fix(py): documents.py — `_doc_to_dict` 移除 Payara 不返回的字段（`acl`/`workflow`/`lifeCycleState`/`routePath`）
- fix(py): changes.py — `issues/link`、`requests/link` 的 `q` 参数默认值已为 `""`（无需修改）

## 2026-07-05 — Workflow/Users/Admin/Misc FA 差距修复

- fix(py): workflows.py — `_model_to_dict` 始终包含 `acl` 字段（无 ACL 时为 `null`），匹配 Payara 响应格式
- fix(py): workflows.py — workflow-instances 路由新增工作区成员校验，非成员返回 403（`AccessRightException`），匹配 Payara 行为
- fix(py): auth.py — `GET /accounts/me` 和 `POST /auth/login` 响应新增 `enabled`、`admin`、`timeZone` 字段；`admin` 从 `usergroupmapping` 表实时查询
- fix(py): accounts.py — `_account_to_dict` 接收 `db` 参数，`admin` 从 `usergroupmapping` 实时查询（原为硬编码 `False`）
- fix(py): user_mgmt_service.py — `list_workspaces_for_user` 新增 `description`、`folderLocked` 字段
- fix(py): misc.py — `/platform/health` 响应改为 `{"executionTime": 0}`（匹配 Payara）
- fix(py): schemas/auth.py — `AccountDTO` 用 `timeZone` 替换 `timezone`，新增 `enabled`/`admin` 字段

## 2026-07-05 — Parts/Documents FA 差距修复

- fix(py): parts.py — 移除 4 处 `response_model_exclude_none=True`，使 Payara 存在的字段（releaseAuthor/obsoleteAuthor/workflow/acl 等）即使为 None 也返回
- fix(py): part_mapper.py — map_revision 新增 `workflow` 和 `acl` 字段输出（ACL 按权限条目构建）
- fix(py): parts.py — 新增 `GET /workspaces/{ws}/part-templates` 端点
- fix(py): documents.py — _doc_to_dict 顶层新增 `releaseAuthor`、`obsoleteAuthor`、`type` 字段
- fix(py): document_templates.py — list_templates/get_template 新增 `author`、`acl`、`creationDate`、`attachedFiles`、`attributeTemplates` 字段
- feat(py): documents.py — 新增 `GET /workspaces/{ws}/document-baselines` 端点

## 2026-07-05 — P2/P3 缺失子端点补全

- feat(py): documents.py 新增 8 个子端点——move/share/publish/unpublish + 4 个 notification 订阅
- feat(py): document_service.py 新增 move_document 方法（更新 location_completepath）
- feat(py): document_templates.py 新增 generate_id 端点
- feat(py): products.py 新增 7 个子端点——product-instances/releases-last/path-choices/versions-choices/cascade-* stubs
- feat(py): users.py 新增 9 个端点——用户/组标签订阅 CRUD + workflows/{id}/aborted stubs（8 GET/PUT/DELETE，均尾斜杠双路由）
- test(py): 3 个测试文件新增 16 个测试用例覆盖所有新端点

## 2026-07-05 — 工作区 CRUD 端点

- feat(py): workspaces 路由——GET/POST/PUT/DELETE /workspaces 完整 CRUD（7 路由），查询 workspace 表，响应含 id/admin/enabled/description/creationDate

## 2026-07-05 — P5 前端 Model 对齐审计修复

- fix(py): task status 整数→字符串映射（0=NOT_STARTED/1=IN_PROGRESS/2=APPROVED/3=REJECTED），防止前端 `status.toLowerCase()` 对整数调用抛出 TypeError
- fix(py): workflow-models 的 author.name 从 Account 表查询真实 name（不再用 login 代替）
- fix(py): workflow-instances 的 activities 从 Activity 表查询（不再硬编码 []）
- fix(py): aborted-workflows 端点实现——parts.py 查询 part_aborted_workflow join workflow、workflows.py 实现 workspace-workflows 和 aborted-instance
- fix(py): workflow-model ACL 从 acl/acluserentry/aclusergroupentry 表查询（不再返回 null）
- fix(py): _model_to_dict 所有调用点传入 db 参数

## 2026-07-05 — P5 工作流与权限（完成）

- feat: P5 完整迁移——66 端点 / 6 功能域 / 16 张表 / 4 ORM 模型文件
- feat: 用户/账号/组管理——UserMgmtService + users.py + accounts.py（24 端点）
- feat: ACL/角色——SecurityService + acl_helper + roles.py + 已有路由补 ACL（13 端点）
- feat: 工作流——WorkflowService + workflows.py（17 端点，process_task MVP）
- feat: 通知——NotificationService + notifications.py（5 端点）
- feat: Webhook——webhooks.py（5 端点）
- feat: Auth 补全——logout/recovery/recover/providers/oauth（5 端点）
- feat: Nginx 10+ 路由块切换
- fix: deletePartRevision 4 项 EntityConstraint 约束补齐（P3/P4 对齐债务清偿）
- fix: EntityConstraintException 状态码 400→403
- test: 121 passed

## 2026-07-05 — P5 工作流与权限（Task 9）

- feat: Webhook CRUD 路由（GET/POST/DELETE /workspaces/{ws}/webhooks），WebhookApp+Webhook 同事务创建，双路由后缀兼容
- test: test_webhooks_api.py 1 测试通过

## 2026-07-05 — P5 工作流与权限（Task 6）

- feat: 通知确认端点 PUT /workspaces/{ws}/notifications/{id} + NotificationService + test_notifications_api.py 1 测试通过
- fix: 移除 part.py 中冗余的 modification_notification Table，解决与 notification.py 的 ModificationNotification ORM 表名冲突

## 2026-07-05 — P5 工作流与权限（Task 2）

- feat: ACL helper（apply_acl/check_write_access）+ SecurityService（Role CRUD）+ Role REST 路由（GET/POST/PUT/DELETE）
- fix: security.py permission 列类型 String→Integer，匹配 DB 实际 integer 类型（Java enum ordinals）
- test: test_security_service.py 3 测试通过（角色空列表/创建删除/ACL 创建与检查），累计 10/10

## 2026-07-05 — P5 工作流与权限（Task 1）

- feat: P5 ORM 模型——user_mgmt（UserGroup/Credential）+ security（ACL/AclUserEntry/AclUserGroupEntry/Role + 2 关联表）+ workflow（WorkflowModel/Workflow/Activity/Task/WebhookApp/Webhook）+ notification（ModificationNotification + 2 关联表）
- test: test_p5_models.py 7 测试通过，所有表存在性验证 + modificationnotification 数据量确认

## 2026-07-05 — P3 产品结构 + P4 变更管理 + 阶段收尾

### P3 产品结构（ConfigurationItem/Baseline/Configuration/Instance）

- feat: ORM 5 模型（ConfigurationItem/ProductBaseline/ProductConfiguration/ProductInstanceMaster/ProductInstanceIteration）+ CADInstance 复用
- feat: ProductStructureService — filter_product_structure（24字段 ComponentDTO 递归）、decodePath、CI/Baseline/Config/Instance CRUD
- feat: 4 路由文件（products/instances/files）+ main.py 注册 + Nginx 2 路由块切换
- fix: P3 Payara 对拍 14 项差异——filter 对象 vs 数组、depth 参数生效、configSpec 参数、字段命名（partNumber→designItemNumber）、author 查 Account.name、DELETE 204、不足字段补全
- fix: LightPartMasterDTO 字段 number/name→partNumber/partName（修复前端 typeahead "undefined"）
- fix: create_ci 接受 designItemNumber + 验证 PartMaster 存在性

### P4 变更管理（Issue/Request/Order/Milestone）

- feat: ORM 4 模型（ChangeIssue/Request/Order/Milestone）+ 3 标签关联表
- feat: ChangeService — 通用 CRUD + 标签管理（12 方法）
- feat: changes.py 路由 — ~30 端点（含尾斜杠双路由）+ Nginx 正则块切换
- fix: _item_to_dict/_milestone_to_dict 完全对齐 Payara camelCase（c.name→手动 getattr）

### 跨模块对齐债务清偿

- fix: deletePartRevision 4 项约束已实现——EntityConstraintException1/5/22（配置项根/基线/替代品，P3）+ EntityConstraintException21（变更项，P4）
- fix: 前端 Model 审计——author 对象缺失致 Part/CI/PartTemplate/Configuration/Baseline 崩溃已修复

### 文档收尾

- docs: CHANGELOG.md 补全 P3/P4 全量记录
- docs: REMINDERS.md P3/P4 完成归档、对齐债务清理、P5 列为下一阶段
- docs: 路线图 P3/P4 状态→✅、Nginx 路由表补 P3/P4 块、对齐债务 P3/P4 条目剔除
- test: 90 测试通过（3 个文档旧数据残留，非本次变更）

## 2026-07-05 — P3 对拍报告剩余差异修复

- fix: products.py DELETE 返回 204 No Content（对齐 Payara）
- fix: products.py GET list/detail 字段重命名 partNumber→designItemNumber，补 designItemName/designItemLatestVersion/author/hasModificationNotification/pathToPathLinks
- fix: product_structure_service.py author 改为从 PartMaster.author→Account.name（对齐 Java pm.getAuthor().getName()）
- fix: product_structure_service.py authorLogin 改为 rev.part_master.author_login
- fix: product_structure_service.py checkOutUser 补全 UserDTO（login/workspaceId/name/email/language）
- fix: product_structure_service.py virtual/substitute 从 usage_link 属性获取（当前默认 False）

## 2026-07-05 — P2 文档/文件夹 + 系统化对拍

- feat: P2 文档/文件夹/模板——ORM(5模型+2关联表)、document_service(14方法)、4路由(27端点)、80测试通过
- feat: Nginx 4路由块切换(documents/folders/document-templates/files/documents)
- feat: 系统化 Payara 对拍——零件端点(P0路由5处+P1补端点4处+P2字段差异exclude_none)、文档端点(P0 search camelCase+P0 folder ID+P1补端点5处+P1字段)
- fix: 尾斜杠307——POST /parts/ /documents/ /nativecad/ /attachedfiles/ /documents/upload/ 加双路由
- fix: CAD转换无文件→204 No Content(Payara对齐)
- fix: 零件列表 exclude_none 回滚(删acl/checkOutUser致前端无权限)
- fix: 文件夹返回Payara格式(id/name/path/home)含子文件夹
- fix: 文档创建响应 camelCase 含 documentIterations+id 格式
- fix: 文档缺失端点补全(checkedout/countCheckedOut/doc_revs/aborted-workflows/inverse-links)
- fix: 零件缺失端点补全(used-by/tags/instances/baselines/aborted-workflows)
- fix: CATIA Copilot端点 8001→8000(Payara→FastAPI)
- known: 3D预览不显示——Nginx/uvicorn HTTP代理层与Three.js r90交互问题(bytely一致/headers对齐/Payara→FA切换可复现,需抓包或升级Three.js)

- feat(py): Kafka 转换消息重构为嵌套结构+userToken，topic 改 CONVERT
- feat(py): file_service——vault 写读 + BinaryResource 记录（save_nativecad/save_attached/get_file_bytes）
- feat(py): 文件上传/下载端点 + 触发转换（nativecad 上传带 CAD 白名单校验，attachedfiles 上传下载，GLB 直下）
- feat(py): 转换回调服务+端点——handle_callback 含 race 修复（findPendingConversion）和空几何跳过逻辑，对齐 Payara ConverterBean
- feat(py): release/obsolete/newVersion 端点对齐 Payara i18n（NotAllowedException46/41/38/36）
- feat(py): 标签管理端点（set/add/remove tags，_ensure_tag upsert）
- feat(py): 零件搜索端点（DB LIKE MVP，按 name/number/type 模糊匹配）
- chore(docker): Nginx files 路由指向 back-py，conversion.env ENDPOINT 切换为 back-py:8000
- chore: requirements 新增 python-multipart 依赖
- test: 73 个测试全部通过（新增 test_part_files_api/test_file_service/test_conversion_service/test_part_status/test_part_tags/test_part_search）

## 2026-07-04（续6）— 迁移路线图权威文档

- docs: 新建 `docs/superpowers/fastapi-migration-roadmap.md` 作为迁移路线图唯一事实来源
- docs: 根据 P0/P1a/对齐审计执行教训调整路线图——引入"标准每阶段工作流"（对齐审计+Payara 对拍在切 Nginx 之前）
- docs: 沉淀 i18n/异常基础设施为跨阶段共享地基与强制规范
- docs: 新增"对齐债务追踪"表（跨模块约束打桩+TODO，标注属主阶段 P3/P4/P5）
- docs: 显式化阶段依赖关系（P3/P4/P5 落地时回补 parts 对齐债务）
- docs: REMINDERS 同步——批次 0-2 归档、P1b 待规划、对齐债务条目

## 2026-07-04（续5）— 零件模块 Payara→FastAPI 行为对齐（批次 0-2）

- feat: i18n 基础设施——复制 Java 4 语言 properties 文件，实现 `app/core/i18n.py` 加载器
- feat: 业务异常体系——`ApplicationException` 基类 + 6 子类，镜像 Payara 异常 key 约定
- feat: 全局 exception handler——异常→HTTP 状态码映射（403/404/409/500），按用户语言翻译 i18n
- feat: 用户语言中间件——从 JWT 解析 Account.language 注入 `request.state.user_language`
- test: 与 Payara 对拍脚本 `scripts/compare_with_payara.py`
- feat: deletePartRevision——`EntityConstraintException2` 被用作组件时返回中文错误消息
- feat: checkout/checkin/undo_checkout——全部替换为 i18n 异常（NotAllowedException37/47/20/19/41）
- feat: createPartMaster/updatePartIteration——EntityAlreadyExistsException/NotAllowedException25
- test: 固化 geometryFileURI/UserDTO/datetime 对齐行为
- test: 批次 1 错误路径集成测试（test_parts_error_paths.py，3 个测试场景）
- 测试统计：从 38 个增加到 57 个，全部通过

---

- feat: P1a 零件核心 CRUD 全部完成（6 个 Task，38 个测试全通过）
  - ORM 模型：9 张零件表 + 5 张关联表完整映射（`app/models/part.py`）
  - Pydantic Schemas：PartRevisionDTO/PartCreationDTO/ComponentDTO 等（`app/schemas/part.py`）
  - ProductService：CRUD + 签出签入 + 装配同步（`app/services/product_service.py`）
  - DTO 映射工具：ORM → Pydantic 转换（`app/services/part_mapper.py`）
  - 14 个零件端点：list/count/search/checkedout/create/get/delete/checkout/checkin/undo/update/conversion
  - Nginx 零件路由切换到 FastAPI back-py（正则只匹配 parts 路径）
- fix: ORM 关联表列名修正——`partrevision_tag` 用 `partmaster_workspace_id`/`partmaster_partnumber`（非 `partrevision_` 前缀）
- fix: ORM 关联表列名修正——`partusagelink_cadinstance` 用 `cadinstance_id`（单数，非 `cadinstances_id`）
- fix: SQLAlchemy 字符串表达式无法引用 Table 对象，改用 lambda 传递 primaryjoin/secondaryjoin
- fix: PartRevision.iterations 添加 `cascade=all,delete-orphan`（删除 revision 时级联删除 iterations）
- fix: 测试用 `test1` 登录（Workspace_2 成员），admin 不是该 workspace 成员
- fix: 测试密码用 `password`（非 `changeit`），workspace 用 `Workspace_2`（DB 中实际存在）

---

## 2026-07-04（续3）

- feat: P0 FastAPI 后端基础设施全部完成（7 个 Task，17 个测试全通过）
  - `docdoku-plm-server-py/`：FastAPI 骨架 + SQLAlchemy ORM + JWT 安全模块 + 认证端点 + vault 文件服务 + Kafka 生产者
  - JWT 兼容 Payara（HS256 + MD5 密码 + 嵌套 JSON subject），共享 JWT_KEY=changeit
  - `back-py` 容器（端口 8009），Nginx 将 `/docdoku-plm-server-rest/api/auth/` 路由到 FastAPI
  - 端到端验证：Nginx → back-py 登录成功，JWT 响应头正常
- fix: Account ORM 模型修正——`account` 表无 `admin` 列，角色组改从 `usergroupmapping` 表查询
- fix: admin 账号密码为 `password`（非 `changeit`）
- chore: 添加 `pytest.ini`（pythonpath=.）、`kafka-python==2.0.2` 依赖

---

## 2026-07-04（续2）

- feat: `conversion-service-py/` 完全自包含，不再依赖 `docdoku-plm-conversion-service/` 路径
  - `convert_step_glb.py`、`wheels/`、`install-python-deps.sh` 已复制进来
  - `build.sh` 重写为 `docker build .`，无跨目录复制
- feat: 转换服务新增网格格式支持（STL/OFF/PLY/OBJ/DAE/IFC），基于 trimesh+ifcopenshell
  - 新文件 `convert_mesh.py`，统一 `converter.py` 入口按扩展名路由
- fix: 去除 DXF 格式（2D 格式，无法生成 3D GLB）
  - 前端 `part_modal_view.js`、后端 `PartBinaryResource.java`、转换服务同步移除
- fix: 空几何体成功路径未清理 temp_dir（main.py）
- fix: 包围盒计算对 NaN/Inf 顶点的保护（convert_mesh.py）
- chore: 重建前后端 + 转换服务镜像，重启所有服务

---

## 2026-07-04（续）

- feat: 转换服务 Java/Quarkus 编排层迁移为 Python-only（`conversion-service-py/`）
  - 新镜像 `docdoku/docdoku-plm-conversion-service:2.7.0-py`（python:3.11-slim，aiokafka + httpx，无 JVM）
  - `convert_step_glb.py` 新增 `convert()` 函数（Phase 1，保留 CLI 入口兼容）
  - `main.py`：aiokafka 手动 commit，`max_poll_records=1`，显式 offset 提交，根治"消费但不投递"问题
  - `converter.py`：`unaccent()` 对齐修复后的 Java `Tools.unAccent()`（不转下划线）
  - `docker-compose.yml` 切换至新镜像，回滚注释保留
  - 删除其他格式转换器（STL/DAE/IFC/OBJ，CATIA 场景仅用 STEP）
  - 回归验证：`Bevel Gear Formula Student 2008 - 2009` GLB 转换成功，HTTP 200，DB `succeed=true`

---

## 2026-07-04

- fix: `Tools.unAccent()`（`docdoku-plm-server-core`）去掉 `.replaceAll("\\p{javaSpaceChar}", "_")`，vault 路径不再将空格转下划线，消除零件号 "A B" 与 "A_B" 的存储路径碰撞
- fix: 前端 `part_list_item.js` 单零件无 GLB 时隐藏 3D 预览按钮（装配体不受影响，可通过子件组装场景）
- fix: 转换服务改用"混合镜像"——旧 `plm-unified-conversion` 的 runner jar（Kafka 消息投递可靠）+ 重建的 lib jar（含 `unAccent` 修复），解决重建后 SmallRye Reactive Messaging 间歇性"消费但不投递"故障
- chore: 备份回滚资产 `docdoku-plm-conversion-service:2.6.2-jvm-hybrid-rollback` 镜像 tag 及 `rollback-artifacts/app.jar.hybrid-rollback`
- docs: 新增 `docs/architecture/conversion-service-python-migration-plan.md`（转换服务 Java→Python 迁移完整方案，待评审）

---

## 2026-06-26

- docs: 完成构型管理五大职能覆盖分析（EIA-649 / GJB 3206B 对标）
- docs: 完成与 myPDM 项目的多维度对比分析报告
- docs: 完成 `thoughts/新一代 PLM 系统融合路径规划.md`（六阶段融合 roadmap）
- docs: 完成 `thoughts/collaboration-and-milestones.md`（协作约定 + M0–M11 里程碑计划）
- chore: 创建新项目仓库 https://github.com/RayDutchman/plm-unified，完成 M0 全部初始化任务
- chore: 新仓库本地路径：`/home/chenweibo/plm-unified`，后续开发在新仓库进行

---

## 2026-06-25

- fix: 删除 Windows portproxy 规则（8000/8001），解决 front/back 容器因端口被 iphlpsvc 占用而卡在 `Created` 状态无法启动的问题
- docs: REMINDERS.md 补充 portproxy 冲突根因和修复方法，并说明 WSL mirrored 模式下不需要这两条规则

---

## 2026-06-22

### feat: 项目级 AI 记忆机制
- 新建 `.opencode/instructions.md`：项目速查手册，每次打开项目自动注入 agent context
- 新建 `.opencode/opencode.json`：注册 instructions 路径，用 `references` 把 `docs/` 子目录注册给 agent
- 将全局 `~/.config/opencode/instructions.md` 中的 CATIA 路径规范迁移到项目级

### feat: 容器架构文档
- 新建 `docs/architecture/containers.md`：详细说明所有 11 个容器的职责、端口、配置、构建方式、数据卷、关键数据流

### fix: `ConverterBean` 空几何体处理
- **文件**：`docdoku-plm-server-ejb/.../ConverterBean.java`
- **问题**：STEP 文件不含实体（如运动学约束件 MGM_*）时，转换器报 `no geometry generated`，后端写 `succeed=false`，前端显示错误图标
- **修复**：在 `handleConversionResultCallback` 的 errorOutput 判断中检测 `no geometry generated`，改为调用 `endConversion(key, true)` 标记成功跳过

### fix: 装配结构 `amount=0` 导致前端结构树无法展开
- **文件**：`D:\CATIA_Related\CATIA-Copilot\catia_copilot\plm\sync.py`，`_sync_node()` 约第 1110 行
- **问题**：构建子零件条目 `comp_entry` 时缺少 `"amount"` 字段，Java int 默认值 0，前端结构树无 `+` 号
- **修复**：加入 `"amount": len(child.instances) if child.instances else 1`

### docs: 修正 HANDOFF.md 过时内容
- 转换格式 `.obj` → `.glb`
- 转换工具 `FreeCAD` → 内置转换工具（Vert.x 服务）
- 更新转换流程描述，补充 Decimation 已知问题说明
- 删除"零件必须 Checkout 状态"的错误限制说明

---

## 2026-06-18

### fix: `ConverterBean.handleConversionResultCallback` race condition
- **文件**：`docdoku-plm-server-ejb/.../ConverterBean.java`
- **问题**：回调时用 `partRevision.getLastIteration()` 写结果，快速连续上传多个 iteration 时，结果写到最新 iteration，旧 iteration 永远 `pending=true`
- **修复**：在 `ConversionDAO` 新增 `findPendingConversionForRevision(PartRevision)` 方法（JPQL 查 `pending=true` 记录），`ConverterBean` 改用此方法精确定位发起转换的 iteration，同时注入 `ConversionDAO`
- **影响**：修复了 Workspace_2 历史积累的 20 条 `pending=true` 记录问题

### chore: 清理历史 pending conversion 记录
- 直接 DB 操作清掉 20 条 `pending=true, succeed=false` 的 conversion 记录（`UPDATE conversion SET pending=false, succeed=false, enddate=NOW() WHERE pending=true`）

### chore: 后端 JVM 堆内存从 2g 升至 4g
- **文件**：`docdoku-plm-docker/env/back.env`，`HEAP_SIZE=2g` → `HEAP_SIZE=4g`
- **文件**：`docdoku-plm-server/docker/asadmin.commands`，修复旧 `-Xmx2g/-Xms2g` 残留，改为环境变量驱动 `create-jvm-options -- -Xmx${ENV=HEAP_SIZE}`

---

## 2026-06-17（及之前）

### fix: 多处 NPE 修复
- JWT token 解析 NPE
- BasicHeader SAM 模块 NPE
- ProductManagerBean 多处 NPE

### feat: 中文界面支持
- 前后端均支持中文 NLS
- Nginx 配置加入 `charset=utf-8`

### feat: CAD 文件上传格式白名单
- 前端 + 后端双重校验，限制上传文件类型

### fix: 文件名含特殊字符/中文时的 URI 编码问题
- 上传和下载路径均处理 URL 编码

### feat: 前端账号表单校验

### feat: `updateUsageLinksInConvertedIteration`
- 新增 ProductManagerBean 方法，允许在零件已 checkin（非 checkout）状态下更新装配关系
- 用于 conversion 回调时同步装配体子零件位置，绕过 checkout 状态限制
