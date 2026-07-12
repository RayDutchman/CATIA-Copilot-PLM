# FastAPI 迁移遗留清单（Migration Loose Ends）

> 生成日期：2026-07-08 ｜ 更新：2026-07-10（PathData/P2P 完成 + 全量对比修复 + 用户姓名/权限修复合集）
> 范围：Java EE Payara (`docdoku-plm-server`) → FastAPI (`docdoku-plm-server-py`) 后端迁移
> 状态：**核心业务已 100% 走 FastAPI，Payara 在生产链路已被完全绕过**，剩余为功能性 loose ends
>
> 本文件汇总所有未完成/占位/降级项，作为后续收尾的唯一清单。修复某项后请在本文件勾选并同步 `CHANGELOG.md` / `REMINDERS.md`。

## 2026-07-10 进展摘要（全量对比修复合集）

- ✅ **PathData / Path-to-Path Link 域全量实现**：18 端点 + Service CRUD + DFS 环检测 + decodePath 验证
- ✅ **filter configSpec 解析**：字符串→filter 对象映射（latest/released/wip），消除 500
- ✅ **hasPathData 路径格式**：`{ci_id}` → `-1` 转换 + visitor 路径支持
- ✅ **基线创建全量修复**：零件可用性 BFS 校验（对齐 Java getLastCheckedInIteration）+ 响应补 author
- ✅ **用户权限 bug**：membership 字段名修复（readOnly→membership 字符串解析）+ 删除错误 account.enabled 写入
- ✅ **deps 访问控制对齐**：补 workspace.admin_login + usergroup_user 组检查
- ✅ **effectivities SQL 列名**：pre.workspace_id→pre.partmaster_workspace_id
- ✅ **用户姓名全量修复**：tasks/doc_baselines/product_structure/products 补 Account name 查询
- ✅ **PartCreationDTO 422**：补 Field alias + extra=ignore
- ✅ **export-files SQL 列名**：br.fullname/pi.nativecadfile_fullname/bd.target_docrevision_version 全量修正
- ✅ **LOV 表名全错**：listofvalues→lov, listofvaluesattribute→lov_namevalue
- ✅ **groups FK 违规**：create_group 补 db.flush()
- ✅ **parts length=0**：ge=1→ge=0 对齐 Payara getAllPartRevisions
- ✅ **4 个 FA 自创端点删除**：disk-usage/users/{login}/in-progress/notifications
- ✅ **P2P 重复路由删除**：product_configurations.py 重复 POST
- ✅ **baseline parts 端点补齐**：GET /product-baselines/{ci}/baselines/{id}/parts
- ✅ **未使用 resources/ 清理**：删除不进 Dockerfile 的顶层 resources/
- ✅ **对比脚本增强**：错误文本对比 + endpoint_behavior_test.py 行为测试
- ✅ **全量对拍**：158 端点 76 MATCH / 37 MISMATCH（37 个 FA/PY 状态码不一致，大部分为 PY 自身 500）
- ✅ **行为测试**：基线 CRUD + 零件 CRUD + 404 一致性 + 401 拦截 → 10/10 通过

## 2026-07-09 进展摘要（A+B+C 批次）
- ✅ A1 SSL Proxy 切 FastAPI + 修复丢失 cert.key
- ✅ A2 DocumentBaselines 补端点
- ✅ B1 产品配置/基线数据解码填充
- ✅ B2 Product Structure 属性/通知/修改通知
- ✅ C1 WorkspaceManager dead stub→真实
- ✅ C2 Query get/delete 真实化
- ✅ C3 EffectivityDTO 填充
- ✅ 修复 3 个生产 SQL bug

---

## 零、迁移已完成的证据（无需担心的部分）

| 维度 | 结论 | 证据 |
|------|------|------|
| Nginx 生产入口 | Port 80 全部→back-py | `front/nginx.conf` |
| 生产兜底 | 未匹配路由 502 | `front/nginx.conf:495-497` |
| CAD 转换回调 | → FastAPI | `conversion.env` |
| REST 资源覆盖 | 43 Java Resource 全有 Python router | `app/routers/*.py` |
| 迁移任务队列 | tracker.csv 523/523 | 只读归档 |
| 回归测试 | 176 passed / 1 skipped | pytest |
| 全量对拍 | 158 端点 76 MATCH / 37 MISMATCH | `compare_all_endpoints.py` |
| 行为测试 | 基线+零件 CRUD 10/10 | `endpoint_behavior_test.py` |

---

## 一、✅ P0 — PathData / Path-to-Path Link 域

**2026-07-10 已完成**：18 REST 端点 + Service CRUD + DFS 环检测 + decodePath 验证 + ORM 重建 + 降级点回填。见 `c668d31`。

---

## 二、✅ P1 — Importer 导入域（2026-07-10 完成）

**已完成**（分支 `feat/py-query-execution-engine`，对齐 Payara `ExcelParser`/`AttributesImporterUtils`/`ImporterBean`/`PartsResource`）：

| 项 | 状态 | 实现 |
|----|------|------|
| **Excel 解析** | ✅ | `app/services/importers/excel_parser.py`（表头正则 + cell comment 校验 + `|` 多值 + 类型校验） |
| **属性合并** | ✅ | `app/services/importers/attributes_importer_utils.py`（merge 更新/新建/DuplicateEntry/AttributeNotFound + LOV 索引解析） |
| **Import 记录** | ✅ | `Import` ORM 修正 + `import_record.py` CRUD（子表 import_error/import_warning） |
| **导入编排** | ✅ | `ImporterService.import_into_parts`/`dry_run_import_into_parts`（checkout→dtype 写入→checkin，错误门控） |
| **REST 端点** | ✅ | 5 端点接入 `/workspaces/{ws}/parts/...`（import/importPreview/imports/import/delete） |

> 仅 `.xlsx` 属性导入落地；**BOM 导入保留 stub**（Java `BomImporter` 本无实现）。`import_into_path_data` 亦保留 stub。
> ⚠️ **设计分歧（待统一）**：`importer._write_iteration_attributes` 写入 `instanceattribute.dtype`，而既有 `product_manager._sync_instance_attributes` 不写 dtype。刻意为之——保证导入属性可被 `query_executor`（按 `ia.dtype` 过滤）检索。后续可统一 `_sync` 也写 dtype。

---

## 三、✅ P1 — Query 执行引擎（2026-07-10 完成）

**已完成**（分支 `feat/py-query-execution-engine`，对齐 Payara `PartRevisionQueryDAO`/`PathDataQueryDAO`/`ProductManagerBean`）：

| 项 | 状态 | 实现 |
|----|------|------|
| **查询保存** | ✅ | `_save_query`/`_save_query_rule`（递归 queryrule 树 + 子表 + 序列 ID + 同名去重） |
| **PartRevision 执行** | ✅ | `app/services/query_executor.py`（11 前缀路由 + operator + date 区间 + pr.\* 特殊 + 属性 EXISTS + 权限/检入后过滤） |
| **PathData 执行** | ✅ | `run_pathdata_query`（pd-attr-\* + 产品实例路径集合） |
| **context PBS 过滤** | ✅ | `app/services/query_pbs.py`（PSFilterVisitor 遍历 + QueryResultRow + P2P + mergeRows） |
| **QueryResult 序列化** | ✅ | `app/schemas/query_result.py`（按 selects 输出 JSON 数组） |
| **runCustomQuery 端点** | ✅ | `POST /workspaces/{ws}/parts/queries`（run+save+export） |

> 遗留小项（非阻塞）：① 签出隐藏（checkout-by-other 的末迭代 DTO 隐藏）在查询结果路径未做，避免 DetachedInstanceError，其他路径已有保护；② `export=XLS` 由既有 `query-export` GET 端点服务，POST 端点 XLS 返回 JSON 数组；③ pytest 全量 189 passed，仅 10 个预存 seed 数据失败。

---

## 四、🔵 P2 — 剩余 MISMATCH 分析（37 个）

| 分类 | 数量 | 说明 |
|------|------|------|
| FA:200 PY:500 | ~20 | Payara 自身 500（容器降级），非 FA 问题 |
| FA:200 PY:404 | ~8 | Payara 缺端点（如 releases/last、baselines/{id}）— FA 对齐正确 |
| FA:404 PY:403 | 2 | workflow-instances Payara 需要特殊权限 |
| FA:404 PY:500 | ~4 | Payara 自身崩溃 |
| FA:422 PY:500 | 2 | auth/login extra=forbid / documents tags — 非实际 bug |
| FA:500 PY:200 | 1 | baseline parts 路由路径已修复 |

---

## 五、🔵 P2 — 已知局限性

| 项 | 状态 |
|----|------|
| WebSocket /ws 403 | ✅ 2026-07-10 修复（路径对齐 `/docdoku-plm-server-rest/ws` + 补 `WebSocket` 类型注解） |
| OnDemandConverter | deferred（需 LibreOffice 引擎） |
| Payara 容器保留 | Port 85 (8005) 对比用，设计如此 |
| pytest 失败 | 种子数据/测试脆弱性（seed_test_data 需修；含删除"测试工作区"后 test_query_save 依赖缺失） |
| 工作区删除级联 | ✅ 2026-07-10 修复（delete_workspace 完整级联 + replica 模式，保留 account/credential） |
| **邮件通知族未迁移** | ⏳ **已排期全量实现（对齐 Payara NotifierBean）**——详见"八、邮件通知族" |

---

## 八、🟠 邮件通知族全量迁移（planned — 对齐 Payara `NotifierBean`）

> **背景**：审计第二轮（audit-round2）P6-08/P6-01 发现 workflow 审批邮件未发。深查确认这是**系统性缺口**：Payara `NotifierBean`（`docdoku-plm-server-ejb/.../NotifierBean.java`）通过 JNDI `mail/docdokuSMTP`（`Transport.send`）真实发信；本部署有 `smtp`/MailHog 容器（:8003），故 Payara **实际会投递**这些邮件。Python 侧 `app/services/notifier.py` **已具备可用发信基础设施**（`_send_email` → `smtplib` → `smtp:1025` MailHog），但**只实现了 `send_bulk_indexation_success/failure`**，其余全部缺失。
>
> **决策（2026-07-12，用户选 B）**：**补全整个邮件通知族，彻底对齐 Payara**（非仅审批）。基础设施已在，逐个补方法 + 接线触发点即可。

### 待实现方法（对照 `NotifierBean` public API）

| Java 方法 | 触发点（Payara） | Python 现状 |
|-----------|------------------|-------------|
| `sendApproval`（doc / part / workspaceWorkflow 三重载） | `WorkflowManagerBean.instantiateWorkflow`（P6-08）；`Document/PartWorkflowManagerBean.approve/rejectTaskOnX`（P6-01） | ❌ 缺（`task_manager.process_task`、`workflow_manager.instantiate_workflow` 已留 TODO 锚点） |
| `sendStateNotification` | 文档审批推进且 step 变化时（发订阅者） | ❌ 缺 |
| `sendIterationNotification` | 新迭代 checkin（发订阅者） | ❌ 缺 |
| `sendTaggedNotification` / `sendUntaggedNotification`（doc + part） | 打/去标签（发订阅者） | ❌ 缺 |
| `sendPasswordRecovery` | `AuthResource` 密码恢复 | ⚠️ 半：P8-04 已写 `passwordrecoveryrequest`（UUID token），**未发邮件** |
| `sendWorkspaceDeletionNotification` / `sendWorkspaceDeletionErrorNotification` | 工作区删除（异步）成功/失败 | ❌ 缺 |
| `sendPartRevisionWorkflowRelaunchedNotification` / `sendDocumentRevision...` / `sendWorkspaceWorkflow...` | 拒绝 + relaunch 后 | ❌ 缺 |
| `sendWorkspaceIndexationSuccess` / `Failure` | 单工作区重建索引 | ❌ 缺（仅 bulk 版已迁移） |
| `sendCredential` | 新建账户下发凭据 | ❌ 缺 |
| `sendBulkIndexationSuccess` / `Failure` | bulk 重建索引 | ✅ 已迁移（`notifier.send_bulk_indexation_*`） |

### 实现要点
- 复用 `notifier._send_email`（MailHog）；收件人：审批取 running task 的 worker email，状态/迭代/标签取订阅者（`documentrevision`/`partrevision` 订阅表 + `tagusersubscription`/`tagusergroupsubscription`），密码恢复取 account email。
- 正文对齐 Java 各 `sendXxxToUser` 的模板 + i18n（复用 `notifier._I18N` 模式 / `core/i18n`）。
- 所有发信 **best-effort**（`try/except` + log，不阻断主流程），与 Payara `@Asynchronous`/吞异常语义一致。
- 触发点接线：workflow_manager / task_manager / document_manager(checkin/tag) / product_manager(checkin/tag) / auth(recovery) / workspace_deletion。
- 单用户 + MailHog 环境下多为休眠态，但功能需与 Payara 对齐；验证方式：触发后查 MailHog（:8003）收件箱。

---

## 六、剩余工作优先级

| 优先级 | 项 | 计划/状态 | 工作量 |
|--------|-----|----------|--------|
| 1 | ~~Importer 域~~ | ✅ 2026-07-10 完成 | — |
| 2 | ~~Query 执行引擎~~ | ✅ 2026-07-10 完成 | — |
| 3 | ~~WebSocket 403~~ | ✅ 2026-07-10 修复 | — |
| 4 | **种子脚本修复** | 权限 + 数据一致性（解阻 pytest 失败；含 test_query_save 硬编码工作区依赖） | 小 |
| 5 | **邮件通知族全量迁移** | ⏳ 已排期（用户选 B，对齐 Payara NotifierBean，见第八节）；基础设施 `_send_email`(MailHog) 已在 | 中 |

---

## 七、统计汇总

| 域 | 状态 |
|----|------|
| 基础设施（SSL/DocBaselines）| ✅ |
| 产品配置/基线/结构降级 | ✅ |
| WorkspaceManager/Query读删/EffectivityDTO | ✅ |
| PathData / Path-to-Path Link | ✅ |
| 用户姓名/权限/effectivities/LOV/export-files SQL | ✅ |
| configSpec/hasPathData/baseline校验 | ✅ |
| **Importer 导入** | ✅ 2026-07-10 完成 |
| **Query 执行引擎** | ✅ 2026-07-10 完成 |
| **WebSocket** | ⏳ 待排期 |
| **邮件通知族（NotifierBean 全量）** | ⏳ 已排期（见第八节） |

> 核心业务完整。剩余：**WebSocket 修复**、**种子脚本修复**（解阻 10 个 pytest 失败）、**邮件通知族全量迁移**（第八节）。
