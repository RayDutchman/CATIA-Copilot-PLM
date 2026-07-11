# FastAPI 迁移审计问题修复实施计划（FIX-PLAN）

> **For agentic workers:** 本计划配合 subagent 编排执行。修复 subagent **只编辑其认领文件包内的文件**，**不跑 pytest、不跑脚本、不 commit、不部署**。所有验证（pytest / validate_sql_columns / 在线 smoke）、部署（docker）、`git commit` 由**主 agent 在每批结束统一执行**。步骤用 `- [ ]` 复选框跟踪。

**Goal:** 按严重级分批修复 `docs/migration/audit/00-index.md` 记录的 26 CRITICAL / 30 HIGH / 47 MEDIUM / 16 LOW 问题，每批产出可验证、可回滚的增量。

**Architecture:** 修复按「**文件包（file package）**」为最小不可分割单元组织。同一文件的所有待修问题归入同一文件包；同一批次内并行的 subagent 认领的文件包**两两文件不相交**（见附录 A 全局所有权矩阵），从根本杜绝写冲突。跨批次串行，同一文件可在不同批次重复出现（行号漂移由主 agent commit 后、下批 subagent 基于最新代码重新定位解决）。

**Tech Stack:** FastAPI + SQLAlchemy（raw SQL 为主）+ PostgreSQL 13 + pytest。后端容器 `docdoku-plm-docker-back-py-1`，Payara 对拍容器 `:8005`，FastAPI 直连 `:8009`。

## Global Constraints

- **DB 真值源唯一**：任何裸 SQL 表名/列名修改前，必须 `docker exec docdoku-plm-docker-db-1 psql -U changeit -d docdokuplm -c "SELECT column_name FROM information_schema.columns WHERE table_name='<表>';"` 核实。
- **subagent 铁律**：只读 + 只写自己认领的文件；**禁止** `pytest`/`git`/`docker`/改其它文件/派生子 agent/TodoWrite。
- **主 agent 独占**：验证、部署、commit、跨文件重构决策、行号复核。
- **登录**：`POST /docdoku-plm-server-rest/api/auth/login {"login":"test1","password":"password"}`，JWT 在响应头 `jwt`。
- **提交信息**：Conventional Commits（`fix:` / `refactor:` / `test:`），每批一个或多个原子 commit。
- **部署**：`docker build -t docdoku-plm-docker-back-py:latest . && docker compose up -d --force-recreate --no-deps back-py`（热修可 `docker cp`+`docker restart`）。
- **pytest 基线**：当前 84 failed（Workspace_2 缺失导致），批次 0 完成后应回到 ~272 passed；此后**任何批次不得引入新的 fail**。

---

## 批次总览

| 批 | 主题 | 并行 subagent 数 | 依赖 | 主 agent 验证重点 |
|---|------|:--:|------|------|
| **0** | 种子/测试工作区恢复（建回归门禁） | 0（主 agent 独做） | 无 | pytest 回绿 |
| **1** | P0-a 列名必崩 | 2 | 批 0 | pytest + 在线 smoke effectivity/share |
| **2** | P0-b 级联删除（抽共享函数） | 1 + 主 agent 重构 | 批 1 | 删工作区后 DB 残留核零 |
| **3** | P0-c 数据完整性（深拷贝/迭代） | 2 | 批 2 | checkout→update FK 无 500 |
| **4** | P0-d 产品配置架构 + 迭代 undo 级联 | 2（+brainstorming） | 批 3 | 配置 CRUD 往返一致 + undocheckout 无 500 |
| **5** | P1 语义 CRITICAL | 4 | 批 4 | 各端点行为对拍 Payara |
| **6** | P2 HIGH 机械类（状态码/权限/DTO） | 4 | 批 5 | pytest + 抽样对拍 |
| **7** | P3 configSpec / 缺失端点 | 2 | 批 6 | configSpec 分支对拍 |

> 每批 = 一个会话粒度。主 agent 在批内：① 派 subagent 并行改文件包 → ② 回收后逐包 code review → ③ 统一验证 → ④ commit → ⑤ 更新 CHANGELOG/REMINDERS。

---

## 批次 0：种子/测试工作区恢复（主 agent 独做，无 subagent）

**Why first:** effectivity/baseline/workflow/change 等域在 GD50 无数据，改完无法运行时验证。必须先让 pytest 回绿，才有回归门禁。

> **✅ 已完成（2026-07-11）。方案调整**：原计划重建 `Workspace_2`；经用户决策改为**将测试套件整体重定向到已有真实数据的 GD50 工作区**（test1 为其 admin），不重建 Workspace_2、不跑 seed 脚本。仅改测试代码 + 修测试数据（DB），不动项目代码。

- [x] **Step 1:** 读 `scripts/seed_test_data.py` 全文——确认它不创建 workspace 本身。（方案调整后未使用该脚本）
- [x] **Step 2（调整）:** 全量替换 33 个 `tests/test_*.py` 的 `WS="Workspace_2"`/硬编码 → `GD50`；`test_parts_error_paths` 组件件改 `GD50_Frame-A`；`test_import_record` USER→`test1`；`test_query_save` workspace→`测试工作区`；conversion 写文件测试隔离到 `temp_vault`。
- [x] **Step 3（调整）:** DB 测试数据修复——补 `folder` GD50 根记录、test1@GD50 membership `readonly`→false、重建 `测试工作区`+用户 e。
- [x] **Step 4:** `pytest -q --ignore=tests/test_vault.py` → **278 passed / 1 failed**（超 ~272 目标）。
- [x] **Step 5:** 批次 0 后稳定基线 = **278 passed / 1 known-fail（test_i18n_bypass，part.py 硬编码 HTTPException，属代码问题）**。后续批次以此判定「无新增 fail」。
- [x] **Step 6:** commit：`test: retarget regression suite to GD50 workspace`

> ⚠️ `test_vault.py` 收集错误（缺 `part_geometry_path`）在批次 6 的 X-6 修复；批次 0~5 用 `--ignore=tests/test_vault.py` 跑。

---

## 批次 1：P0-a 列名必崩（2 并行 subagent）

**主 agent 已 information_schema + 源码二次核实全部属实。** 改动小、风险低、见效快，用于建立部署+验证流程。

### 文件包 PKG-effectivity → Subagent A
**Files:** `app/models/product/effectivity.py`、`app/routers/effectivity.py`、`app/services/effectivity_manager.py`

- [x] **B-1** `models/product/effectivity.py:13-20`：删除伪列 `creation_date=Column("creationdate")`、`type_effectivity=Column("type_effectivity")`；`start_lot=Column("startlot")`→`Column("startlotid")`、`end_lot=Column("endlot")`→`Column("endlotid")`。DB 真值列：`id,dtype,description,name,configurationitem_id,configurationitem_workspace_id,enddate,startdate,endlotid,startlotid,endnumber,startnumber`。
- [x] **B-2** `routers/effectivity.py:139-142`：INSERT 列 `workspace_id`→`partmaster_workspace_id`（DB 表 partrevision_effectivity 列为 `partmaster_workspace_id,partmaster_partnumber,partrevision_version,effectivity_id`）。
- [x] **B-3** `services/effectivity_manager.py:15-16,98-100`：`get_effectivity`/`delete_effectivity` 移除 `AND workspace_id=:ws`（effectivity 表无此列）；改为经 `partrevision_effectivity` 关联表验证归属：`... WHERE id=:id AND EXISTS(SELECT 1 FROM partrevision_effectivity pre WHERE pre.effectivity_id=:id AND pre.partmaster_workspace_id=:ws)`。
- [x] **B-9**（顺带）`routers/effectivity.py:164,179`：`/effectivities/{id}` 补 `/workspaces/{ws}` 前缀 → `/workspaces/{workspace_id}/effectivities/{id}`，函数签名加 `workspace_id: str`。
- [x] **B-12**（顺带）`create_effectivity`：按 dtype 补必填校验（SERIAL→startnumber、DATE→startdate、LOT→startlotid 非空，否则 `raise CreationException`）。

### 文件包 PKG-share → Subagent B
**Files:** `app/routers/share.py`、`app/services/share_manager.py`

- [x] **X-1** `routers/share.py:80`：SELECT 列 `expire_date`→`expiredate`（DB sharedentity 列含 `expiredate`）。
- [x] **X-2** `routers/share.py:206-207,245-246`：将 `_check_workspace_member` 移到 `public_shared` 检查之后——仅当 `not doc.public_shared and login is not None` 时才校验成员身份（对齐 Java 先公开后认证）。
- [x] **X-3** `services/share_manager.py:15,26`：`WHERE se.password=:uuid`→`WHERE se.uuid=:uuid`；`SELECT expire`→`SELECT expiredate`。

### 主 agent 批 1 收尾
- [x] 逐包 code review（diff 对照上面规格 + DB 真值）。
- [x] 部署 back-py。
- [x] 在线 smoke（test1 JWT）：`GET /workspaces/GD50/effectivities/1`（不再 500，返回 404 或数据）；创建/删除 effectivity 往返；`GET /shared/<任一uuid>/documents`（不再因列名 500）。
- [x] `pytest -q --ignore=tests/test_vault.py` = 批 0 基线（无新增 fail）。
- [x] commit：`fix(effectivity): correct ORM/SQL column names and workspace scoping (B-1~B-3,B-9,B-12)` + `fix(share): correct sharedentity column name and public-share auth order (X-1~X-3)`
- [x] 更新 CHANGELOG/REMINDERS（勾除 B-1/B-2/B-3/X-1，修正 Bug #5 状态）。

---

## 批次 2：P0-b 级联删除（主 agent 重构 + 1 subagent）

**核心：抽取 `workspaces.py:610-893` 内联的完整级联删除为单一共享函数，消除 admin.py/workspace_manager.py 的危险单行 stub。** 抽取属跨文件重构，**由主 agent 亲自做**；独立的 baseline/模板级联派 1 个 subagent。

### 主 agent 亲做（重构，不派 subagent）
- [x] **重构** 新建 `app/services/workspace_deletion.py`，函数 `cascade_delete_workspace(db, ws)`：把 `routers/workspaces.py` 的 `delete_workspace` 内联级联体（`SET LOCAL session_replication_role='replica'` + 全部 `_del(...)` + 末尾 `DELETE FROM binaryresource WHERE fullname LIKE '{ws}/%' ESCAPE '\'` + `shutil.rmtree(VAULT_PATH/ws)`）整体迁入。
- [x] **W-1** `routers/admin.py:208-217`：`delete_workspace` 改为调用 `cascade_delete_workspace(db, ws)`。
- [x] **W-3** `services/workspace_manager.py:55-64`：`delete_workspace` 改为调用 `cascade_delete_workspace(db, ws)`（消除单行 stub）。
- [x] `routers/workspaces.py:610` 的端点也改调 `cascade_delete_workspace`（DRY，去重内联体）。
- [x] **W-2** `routers/admin.py:138-143`：`delete_account` 补级联，删 account 前按序清理 `organization_account/gcmaccount/passwordrecoveryrequest/providedaccount/workspaceusermembership/workspaceusergroupmembership/role_user/tagusersubscription` + 处理 `workspace.admin_login` 引用（先逐表 information_schema 核实列名）。

### 文件包 PKG-baseline-cascade → Subagent C（与上面 admin/workspace 文件不相交）
**Files:** `app/services/product_structure.py`（仅 `delete_baseline`，约 652-657）

- [x] **B-4**：`delete_baseline` 补级联，参照 `workspaces.py:753-756` 顺序删 `baselinedpart`→`baselineddocument`→`productbaseline_substitutelink`/`optionallink`/`p2plink`→`partcollection`/`documentcollection`→`productbaseline`；删前查 `productinstanceiteration WHERE productbaseline_id=:bid`，有引用抛 `EntityConstraintException("EntityConstraintException16")`（含 B-8）。

### 文件包 PKG-doctemplate-cascade → Subagent D（文件不相交）
**Files:** `app/services/document_manager.py`（仅 `delete_template`，约 978-980）

- [x] **D-9**：`delete_template` 补级联删 `documentmastertemplate_binres`/`BinaryResource`+vault/`documentmastertemplate_attr`/`instanceattributetemplate`/`acl` 关联（逐表 information_schema 核实）。

> ⚠️ **批内文件不相交校验**：主 agent 改 admin.py/workspace_manager.py/workspaces.py/新建 workspace_deletion.py；Subagent C 改 product_structure.py；Subagent D 改 document_manager.py。三方无交集 ✓。（product_structure.py 的 PR-CRIT-1、document_manager.py 的 D-1/D-3 留到后续批次，不在本批并行触碰。）

### 主 agent 批 2 收尾
- [x] 部署 + smoke：建临时工作区→塞数据→`DELETE /admin/workspaces/{ws}`→DB 核 `binaryresource WHERE fullname LIKE 'ws/%'`、各子表残留全 0；vault 目录已删。
- [x] `pytest` 无新增 fail。
- [x] commit（分 refactor + 各 fix）。更新 CHANGELOG/REMINDERS。

---

## 批次 3：P0-c 数据完整性（2 并行 subagent）

### 文件包 PKG-product_manager → Subagent E
**Files:** `app/services/product_manager.py`

- [x] **P-1** `_copy_iteration_files`（约 1283-1297）：checkout 复制 `part_iteration_usagelink` 时，对每条 PartUsageLink **深克隆**（`INSERT INTO partusagelink(...) SELECT ... RETURNING id` 建新 component_id，再写关联表引用新 id），而非复用旧 `component_id`。验证 `__do_sync_components`（约 670-673）删旧 link 时不再触发 `partiteration_partusagelink.component_id` FK 冲突。**注意与 2026-07-11 已修的 instanceattribute 深拷贝是不同表，勿混淆。** ✅ 同时修复了 `__do_sync_components` 孤儿 PartUsageLink 删除未清理 `partusagelink_cadinstance`/`pusagelink_psubstitutelink`/`cadinstance` 的连带 FK bug（原注释误称自动级联）。
- [x] **PR-MED-2**（顺带）`__do_sync_components`（约 694-713）：写 cadInstance 时若 `rotation_type` 为 None，按有 m00→`MATRIX`、否则→`ANGLE` 推断（注意 Java 枚举实为 `ANGLE` 非 `ANGULAR`）。

### 文件包 PKG-document_manager → Subagent F（与 product_manager.py 不相交）
**Files:** `app/services/document_manager.py`

- [x] **D-1** `checkout`（约 366-393）：新迭代补 `_copy_linked_documents` + `_copy_instance_attributes`（对齐 `DocumentManagerBean.java:942-956`，深拷贝，勿共享行）。✅ 并补 `db.flush()`（session autoflush=False，裸 SQL INSERT 前须先落地新迭代行）。
- [x] **D-3** `update_iteration`（约 672-715）：补 instanceAttributes 全量替换（DELETE+INSERT，模式同 linkedDocuments）；加 checkout 用户 + 末迭代身份校验（对齐 `DocumentManagerBean.java:1385`）。新增 `user_login` 可选参数，router `document.py` 侧已连线传 `current_user.login`。
- [x] **D-12**（顺带，约 696-700）：写 documentlink 的 `target_workspace_id` 从 `ld.get("workspaceId")` 取，非恒当前 ws。
- [x] **D-10**（顺带）`list_folders`（约 897-904）：无 parent_path 时只返回 `parentfolder_completepath = workspaceId` 的直接子。

### 主 agent 批 3 收尾
- [x] 部署 + smoke：GD50 零件 checkout→改子件→checkin 无 500（P-1）；文档 checkout 后 linkedDocs/attrs 保留（D-1）；update_iteration 属性生效（D-3）。
- [x] `pytest` 无新增 fail（278 passed / 1 known-fail test_i18n_bypass）。commit。更新文档。

---

## 批次 4：P0-d 产品配置架构（brainstorming + 1 subagent）

**PR-CRIT-1/2 强耦合（写错表 + ID 不关联），须一次性重构。先 brainstorming 定 ID 方案。**

- [x] **主 agent Step 0（已完成 2026-07-12，brainstorming）**：决策 = **方案A：保持 ProductConfiguration 为独立实体**（对齐 Java），不做 joined inheritance、不回填 productbaseline。
  > **决策记录（三重佐证）**：① Java `core/configuration/ProductConfiguration.java:47-51` 是**独立 `@Entity`**（非 `extends ProductBaseline`），有自己的 `@GeneratedValue(IDENTITY) int id`；② DB `information_schema`：`productconfiguration` 有独立 `productconfiguration_id_seq`；FK `fk_prdcfg_substitutelink_productbaseline_id`/`fk_prdcfg_optionallink_productbaseline_id` 的 `productbaseline_id` 列（命名误导）实际**引用 `productconfiguration.id`**；③ Python `product_configuration.py` 模型 id 已映射该 seq，读取路径 `_config_substitute_paths`/`_optional_paths`（`WHERE productbaseline_id=:config.id`）**已正确**。
  > **结论**：**PR-CRIT-2 为审计误报**（读写主键已一致），降级为「验证读写一致」的空操作。真正 bug 仅 **PR-CRIT-1**（`create_config` 写错表 + 把路径字符串当 dict）。
  > **PR-CRIT-5 修正**：研究 Java `ProductInstanceManagerBean.updateProductInstance:332-384` 确认它**就地改指定迭代（URL 含 `/{iteration}`），不创建新迭代**；audit/FIX-PLAN 原述「创建新迭代」有误，按 Java 真值修（补 `/{iteration}` 路由 + 就地改该迭代的 iterationNote/instanceAttributes/linkedDocuments）。

### 文件包 PKG-product-config → Subagent G
**Files:** `app/services/product_structure.py`（`create_config` 约 679-697）、`app/models/configuration/product_configuration.py`、`app/routers/product_configurations.py`、`app/routers/product_instances.py`、`app/routers/product_files.py`

- [x] **PR-CRIT-1** `create_config`：substitute/optional 改写 `prdcfg_substitutelink(productbaseline_id, substitutelinks)` / `prdcfg_optionallink(productbaseline_id, optionalusagelinks)`（路径字符串），停止写 partsubstitutelink / `UPDATE partusagelink SET optional`。✅ 同时补 `delete_config` 清理 prdcfg_* 关联行（FK NO ACTION），恢复写/删对称。
- [x] **PR-CRIT-2** 按 Step 0 决策修 `product_configuration.py` 模型 + `product_configurations.py:63-78` 读取，使写入与读取主键一致。✅ **验证为误报**：模型 id 已映射 productconfiguration_id_seq、读写均用 config.id，FK 实际指向 productconfiguration.id，无需改动。
- [x] **PR-CRIT-3** `product_instances.py:252-257` `rebase_instance`：实现真实 rebase（创建新 ProductInstanceIteration + 关联基线），去掉空 `Response(204)` 桩。✅ 简化实现（新迭代+新 baseline+继承 note），未深拷贝 collections/pathData。
- [x] **PR-CRIT-5** `product_instances.py:107-155` `update_instance`：路由补 `/{iteration}`，就地改指定迭代（**Java 真值：非创建新迭代**），处理 instanceAttributes。
- [x] **PR-CRIT-4** `product_files.py:14-23` upload：写物理文件的同时创建 `BinaryResource` DB 行 + `prdinstiteration_binres` 关联，返回 201+fullName。

### 文件包 PKG-iteration-undo → Subagent G2（与 Subagent G 文件不相交）
**Files:** `app/services/product_manager.py`（`undo_checkout` 约 474-508）、`app/services/document_manager.py`（`undo_checkout` 约 650-679）

> **背景（批 3 smoke 新发现，已主 agent 对拍 Payara 确认属实）**：零件/文档 `undo_checkout` 用 `db.delete(last)` 删末迭代，但 SQLAlchemy 只自动清理 secondary 关系（part 的 attached_files/geometries/components 关联行），**不清理**仅存在于裸 SQL 层的子表。Java `ProductManagerBean.undoCheckOutPart:404-408` 靠 `PartIteration` 实体的 `orphanRemoval=true`/`CascadeType.ALL`（instanceAttributes/instanceAttributeTemplates/linkedDocuments）级联删除全部子行；Python ORM 的 `PartIteration`/`DocumentIteration` 均无这些子关系。所有相关 FK 均为 NO ACTION → 删末迭代必 500。

- [x] **P-14**（CRITICAL）`product_manager.py:474-508` `undo_checkout`：`db.delete(last)` 前，按 FK 依赖顺序清理末迭代子表 + 孤儿深拷贝行。需删：`partiteration_attribute`（+孤儿 `instanceattribute`）、`partiteration_pathdata_attr`（+孤儿 `instanceattributetemplate`）、`partiteration_documentlink`（+孤儿 `documentlink`）、`partiteration_usagelink`（+孤儿 `partusagelink`/`partusagelink_cadinstance`/`cadinstance`——复用批 3 `__do_sync_components` 的孤儿清理逻辑，可抽为共享私有方法）、`partiteration_binres`/`partiteration_geometry`（对应 `BinaryResource` 已由现有 LIKE 删除覆盖）。DB 真值：`partiteration_attribute(workspace_id,partmaster_partnumber,partrevision_version,iteration,instanceattribute_id,attribute_order)`；FK `fk_partiteration_attribute_iteration` 现为 NO ACTION。验证：带属性+组件的 GD50 零件 checkout→undocheckout 无 500，子表残留全 0。✅ 抽取 `_delete_orphan_usage_links` 共享方法；smoke（Assem1）checkout→iter2(ul34/pul58/cad96)→undocheckout HTTP 200 精确回到基线(ul17/pul41/cad62)。
- [x] **D-14**（CRITICAL）`document_manager.py:650-679` `undo_checkout`：同理，`db.delete(last)` 前清理 `documentiteration_attribute`（+孤儿 `instanceattribute`）、`documentiteration_documentlink`（+孤儿 `documentlink`）、`documentiteration_binres`（BinaryResource 已由现有 LIKE 删除覆盖，但关联行需先删）。验证：带属性+链接的文档 checkout→undocheckout 无 500。✅ smoke（D14TEST）checkin→checkout iter2(attrs4/links2/ia4)→undocheckout HTTP 200 精确回到基线(attrs2/links1/ia2)。

### 主 agent 批 4 收尾
- [x] 部署 + smoke：创建产品配置→读回 substitute/optional 一致（PR-CRIT-1/2）；产品实例文件上传后可下载（PR-CRIT-4）；带属性+组件零件 checkout→undocheckout 无 500 且子表残留全 0（P-14）；带属性文档 checkout→undocheckout 无 500（D-14）。
- [x] pytest 无新增 fail（278 passed / 1 known-fail test_i18n_bypass）。commit。更新文档。

---

## 批次 5：P1 语义 CRITICAL（4 并行 subagent，文件不相交）

### PKG-workflow → Subagent H
**Files:** `app/routers/workflow.py`、`app/services/workflow_manager.py`
- [ ] **WF-1** `workflow.py:60-65`：aborted-workflow-list 改为按 workflowId 查持有者→返回持有者 aborted 列表（对齐 `WorkflowManagerBean.java:387-419`）。
- [ ] **WF-2** `workflow.py:68-74`：list_wwf 返回 `workspace_workflow.*`（UUID id）而非 `workflow.*`。
- [ ] **WF-3** `workflow_manager.py:275`：`currval` 改 `INSERT ... RETURNING id`。
- [ ] **WF-4** `workflow_manager.py:260-364`：补 notifier.sendApproval 通知（若 notifier 已有接口）。

### PKG-task → Subagent I
**Files:** `app/services/task_manager.py`、`app/routers/tasks.py`
- [ ] **TASK-1** `task_manager.py:171-271` `process_task`：工作流完成时更新持有者（文档/零件）`lifeCycleState`（对齐 Java 各 WorkflowManagerBean）。
- [ ] **TASK-2** `tasks.py:204-223`：process_task 返回 204（如需对齐 Payara，见决策项）。

### PKG-change → Subagent J
**Files:** `app/routers/change_common.py`、`app/services/change_manager.py`
- [ ] **CH-1** `change_common.py:35-41`：`_get_acl_dict` 填充 `userGroupEntriesMap`（group_id→permission）。
- [ ] **CH-4** `change_common.py:179-183`：`_set_affected_parts` iteration 从 body 取，不硬编码 1。
- [ ] **CH-2** `change_manager.py:141-163`：`update_item` 加白名单，排除 name/id/author_login。
- [ ] **CH-5** `change_common.py:171-184`：`_set_affected_*` 补 ACL 写权限检查。

### PKG-query → Subagent K
**Files:** `app/services/query_executor.py`、`app/schemas/query_result.py`
- [ ] **Q-1** `query_executor.py:312-345`：`run_part_query` 补 checkout-by-another-user 隐藏末迭代。
- [ ] **Q-2** `query_executor.py:214`：author.* 分支改 `_cmp(f"acc.{sub}", ...)` + `_safe_ident(sub)`，支持 email/language。
- [ ] **Q-11**（顺带）`query_executor.py:181`：`_pr_leaf` fallback 加安全列名白名单，非白名单返回 `1=1`。

> Q-3（导出端点，涉及 `routers/parts.py`）留到批 6，避免与其它 parts.py 修改并行冲突。

### 主 agent 批 5 收尾
- [ ] 部署 + 对拍 Payara（各端点行为）。pytest 无新增 fail。commit（分域）。更新文档。

---

## 批次 6：P2 HIGH/MEDIUM 机械类（4 并行 subagent）

改动模式一致（状态码 204、补权限、补 DTO 字段、缺端点），高度可并行。**按文件分包，保证不相交。**

### PKG-parts-batch → Subagent L
**Files:** `app/routers/part.py`、`app/routers/parts.py`、`app/services/part_mapper.py`
- [ ] **P-2** retryConversion（part.py:620）实发转换。**P-3** newVersion（part.py:190）加 body/workflow/acl。**P-4** publish/unpublish/acl 返回 204。**P-5** publish/unpublish 加写权限。**P-6/Q-5** parts.py:392 `post_queries` 无 ws 返回 400。**Q-3** parts.py:501 query-export 改 POST+补导出已存查询端点。**P-7** part_mapper.py:184 JOIN 加 workspace_id。**P-8** parts.py:146 收窄 except。

### PKG-documents-batch → Subagent M
**Files:** `app/routers/document.py`、`app/routers/documents.py`、`app/routers/document_templates.py`、`app/routers/document_template_files.py`、`app/routers/folders.py`
- [ ] **D-2** 补 4 文件 rename/remove 端点。**D-4** create_document 补字段透传。**D-5** 6 端点 204。**D-6** 补 POST share。**D-7** new_version 连线 role_mapping。**D-8** 模板 update 实现属性持久化。**D-11** publish 加权限。**D-13** folders 删重复装饰器。

### PKG-workspace-batch → Subagent N
**Files:** `app/routers/accounts.py`、`app/routers/workspace_memberships.py`、`app/routers/workspaces.py`、`app/services/user_manager.py`、`app/services/organization_manager.py`
- [ ] **W-4** GCM 实现。**W-5** remove_user 补 membership/group 清理。**W-6** create_workspace 补 enabled 策略。**W-7** add_user group 改 Query 参数。**W-9/W-11** delete_group 补 ACL 检查 + 删 membership。**W-14** organization_manager 修 organization_account 写入或删死代码。

### PKG-crosscutting-batch → Subagent O
**Files:** `app/routers/tags.py`、`app/routers/auth.py`、`app/routers/notifications.py`、`app/services/notification_manager.py`、`app/services/vault.py`、`app/services/converter.py`、`app/services/binary_storage.py`
- [ ] **X-5** 删 tag 先清关联表。**X-6** vault.py 补 `part_geometry_path` 并替换 converter/binary_storage 内联。**X-7** 补 GET notifications。**X-8** auth recover 用 DTO 取 newPassword。**X-9** create_tags 返回 204。**X-12** notification list 按 ackauthor_login 过滤。

### 主 agent 批 6 收尾
- [ ] **移除** `pytest --ignore=tests/test_vault.py`（X-6 已补符号，test_vault 应可收集）。跑全量 pytest 无新增 fail。
- [ ] 部署 + 抽样对拍。commit（分域）。更新文档。

---

## 批次 7：P3 configSpec / 缺失端点（2 并行 subagent）

### PKG-products-configspec → Subagent P
**Files:** `app/routers/products.py`、`app/services/product_structure.py`、`app/services/products/path_data_service.py`、`app/services/products/path_to_path_service.py`
- [ ] **PR-HIGH-1** filter 补 linkType/diverge。**PR-HIGH-2** list_instances 3D 按 configSpec + pi- 解析。**PR-HIGH-3** searchPaths 补 configSpec/diverge。**PR-HIGH-4** cascade 补 configSpec/path。**PR-HIGH-5** P2P sourceComponents/targetComponents 做 decodePath。**PR-MED-1** path_data_service INSERT 补 dtype。**PR-MED-4** get_product_instance 补 acl。

### PKG-baseline-types → Subagent Q（与 products.py 不相交；product_structure.py ⚠️ 与 P 冲突）
> ⚠️ **product_structure.py 被 Subagent P（PR-HIGH-1）与 Subagent Q（B-6）同时需要 → 冲突！** 解决：B-6 归入 Subagent P（合并 products 相关），Subagent Q 只认领 `app/routers/product_baselines.py`、`app/routers/document_baselines.py`。
**Files:** `app/routers/product_baselines.py`、`app/routers/document_baselines.py`
- [ ] **B-5**（CRITICAL）`document_baselines.py:115-167`：文档基线创建补 snapshotDocuments 校验——RELEASED 类型过滤 `status IN (1,2)`、LATEST 类型移除他人签出的末迭代、已存在跳过、空集抛 `NotAllowedException("NotAllowedException66")`（对齐 `DocumentBaselineManagerBean.java:66-78,157-185`）。
- [ ] **B-6** create_baseline 补 EFFECTIVE_DATE/SERIAL/LOT 三类型（**在 product_structure.py 的部分并入 Subagent P**；路由参数提取在 product_baselines.py 由 Q 做）。**B-7** detail 补 configurationItemLatestRevision。**B-15** P2P links 路径前缀对齐 + 补 document-baseline export-files。**B-10** 空文档校验移 service 层抛 NotAllowedException66。

### 主 agent 批 7 收尾
- [ ] 部署 + configSpec 分支对拍（latest/released/wip/baseline）。全量 pytest。commit。更新文档。

---

## 附录 A：全局文件所有权矩阵（防重叠证明）

**规则：同一列（批次）内，每个文件只出现在一个 subagent 行。跨批次可重复。**

| 文件 | 批1 | 批2 | 批3 | 批4 | 批5 | 批6 | 批7 |
|------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| models/product/effectivity.py | A | | | | | | |
| routers/effectivity.py | A | | | | | | |
| services/effectivity_manager.py | A | | | | | | |
| routers/share.py | B | | | | | | |
| services/share_manager.py | B | | | | | | |
| routers/admin.py | | 主 | | | | | |
| services/workspace_manager.py | | 主 | | | | | |
| routers/workspaces.py | | 主 | | | | N | |
| services/workspace_deletion.py(新) | | 主 | | | | | |
| services/product_structure.py | | C | | G | | | P |
| services/document_manager.py | | D | F | G2 | | | |
| services/product_manager.py | | | E | G2 | | | |
| models/configuration/product_configuration.py | | | | G | | | |
| routers/product_configurations.py | | | | G | | | |
| routers/product_instances.py | | | | G | | | |
| routers/product_files.py | | | | G | | | |
| routers/workflow.py | | | | | H | | |
| services/workflow_manager.py | | | | | H | | |
| services/task_manager.py | | | | | I | | |
| routers/tasks.py | | | | | I | | |
| routers/change_common.py | | | | | J | | |
| services/change_manager.py | | | | | J | | |
| services/query_executor.py | | | | | K | | |
| schemas/query_result.py | | | | | K | | |
| routers/part.py | | | | | | L | |
| routers/parts.py | | | | | | L | |
| services/part_mapper.py | | | | | | L | |
| routers/document.py 等文档组 | | | | | | M | |
| routers/accounts.py / workspace_memberships.py / user_manager.py / organization_manager.py | | | | | | N | |
| routers/tags.py / auth.py / notifications.py / notification_manager.py / vault.py / converter.py / binary_storage.py | | | | | | O | |
| routers/products.py | | | | | | | P |
| services/products/path_*.py | | | | | | | P |
| routers/product_baselines.py / document_baselines.py | | | | | | | Q |

**每列校验**：批1(A,B 无交)、批2(主,C,D 无交)、批3(E,F 无交)、批4(G 与 G2 无交——G 改 product_structure/product_configuration/product_configurations/product_instances/product_files，G2 改 product_manager/document_manager)、批5(H,I,J,K 无交)、批6(L,M,N,O 无交)、批7(P,Q 无交，B-6 的 product_structure.py 部分并入 P)。✅ 全批次文件不相交。

---

## 附录 B：主 agent 每批标准流程（SOP）

1. 派本批 subagent（含：文件包清单 + 对应问题规格 + `full-audit-checklist.md` + 相关域报告路径 + 「只写认领文件、禁验证/commit/派生」硬约束）。
2. 回收后逐包 code review：diff 对照规格 + DB 真值 + 相邻文件接口一致性。
3. 部署 back-py。
4. 验证：`pytest -q`（对齐批 0 基线，无新增 fail）+ 本批针对性在线 smoke/对拍。
5. 若失败：主 agent 亲自修或带 review 意见重派对应 subagent（`receiving-code-review`）。
6. 全绿后 commit（Conventional Commits，按域拆原子 commit）。
7. 更新 `docs/CHANGELOG.md` + `docs/REMINDERS.md` + 对应 `docs/migration/audit/*.md` 勾除。
