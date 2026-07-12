# 第二轮审计问题修复实施计划（audit-round2 / FIX-PLAN）

> **For agentic workers:** 本计划配合 subagent 编排执行。修复 subagent **只编辑其认领文件包内的文件**，**不跑 pytest、不跑脚本、不 commit、不部署**。所有验证（pytest / validate_sql_columns / 在线 smoke / Payara 对拍）、部署（docker）、`git commit` 由**主 agent 在每批结束统一执行**。步骤用 `- [ ]` 复选框跟踪。

**Goal:** 按严重级分批修复 `docs/migration/audit-round2/00-index.md`（经独立复核）确认的 **6 CRITICAL / 29 HIGH**，MED/LOW 在末批收尾。每批产出可验证、可回滚的增量。

**Architecture:** 修复按「**文件包（file package）**」为最小不可分割单元组织。同一文件的所有待修问题归入同一文件包；同批次内并行 subagent 认领的文件包**两两文件不相交**（见附录 A 所有权矩阵），杜绝写冲突。跨批次串行，同一文件可在不同批次重复（行号漂移由主 agent commit 后、下批 subagent 基于最新代码重新定位解决）。

**Tech Stack:** FastAPI + SQLAlchemy（raw SQL 为主）+ PostgreSQL 13 + pytest。后端容器 `docdoku-plm-docker-back-py-1`，Payara 对拍容器 `:8005`（或直连 `:8001`），FastAPI 直连 `:8009`。

## Global Constraints

- **DB 真值源唯一**：任何裸 SQL 表名/列名或 FK 依赖判断前，必须 `docker exec docdoku-plm-docker-db-1 psql -U changeit -d docdokuplm -c "\d <表>"` 核实。
- **subagent 铁律**：只读 + 只写自己认领的文件；**禁止** `pytest`/`git`/`docker`/改其它文件/派生子 agent/TodoWrite/skill。
- **主 agent 独占**：验证、部署、commit、跨文件重构决策、行号复核。
- **登录**：`POST /docdoku-plm-server-rest/api/auth/login {"login":"test1","password":"password"}`，JWT 在响应头 `jwt`；常用 `WS=GD50`。
- **Payara 为对齐真值源**：复核已发现原审计有 2 处 Java 断言不准（P6-01 无 releaseDocument、P7-03 非全成全败）；修复前若对 Java 行为有疑，直接打开 Java 源或对拍 `:8001`。
- **提交信息**：Conventional Commits（`fix:` / `refactor:`），每批一个或多个原子 commit。
- **部署**：`docker build -t docdoku-plm-docker-back-py:latest . && docker compose up -d --force-recreate --no-deps back-py`（热修可 `docker cp`+`docker restart`）。
- **pytest 基线**：**282 passed / 1 skipped**（当前基线）；此后**任何批次不得引入新 fail**。涉 500 的 CRITICAL 须在 GD50 有数据环境复测。

---

## 批次总览

| 批 | 主题 | 问题数 | 并行 subagent | 依赖 | 主 agent 验证重点 |
|---|------|:--:|:--:|------|------|
| **1** | 6 CRITICAL（快速止血：500/崩溃/数据损坏） | 6 | 4 | 无 | 各 500/崩溃端点在 GD50 转正常 + pytest |
| **2** | P1 权限/安全 HIGH | 12 | 4 | 批 1 | 越权/信息泄露/FK500 对拍 Payara |
| **3** | P2 workflow/change/baseline/effectivity HIGH | 9 | 4 | 批 2 | 状态码/DTO/校验对拍 Payara |
| **4** | P3 products 结构/实例 + query HIGH | 8 | 3 | 批 3 | configSpec/pathData/importer 对拍 |
| **5** | MED/LOW 收尾 | 40 MED + 24 LOW | 按域报告分包 | 批 4 | pytest + 抽样对拍 |
| **6** | 邮件通知族全量迁移（planned，对齐 NotifierBean） | 9 方法族 | 按文件分包 | 批 5 | pytest + MailHog(:8003) 验证 |

> 每批 = 一个会话粒度。主 agent 在批内：① 派 subagent 并行改文件包 → ② 回收后逐包 code review → ③ 部署 → ④ 统一验证 → ⑤ commit → ⑥ 更新 CHANGELOG/REMINDERS + 勾除本文件。

---

## 批次 1：6 CRITICAL（4 并行 subagent，文件不相交）

**均为定位明确的代码缺陷，多为一处改动即消除 500/崩溃/数据损坏。见效快、风险低，用于建立部署+验证流程。**

### 文件包 PKG-products-crit → Subagent A1
**Files:** `app/routers/products.py`
- [x] **P2-02（C1）** `products.py` `search_ci_numbers`（约 :97）：`_ci_to_dict(db, c)` 参数错序 → 改为 `_ci_to_dict(c, db)`。对照签名 `_ci_to_dict(ci, db)`（约 :50）。验证：`GET /workspaces/GD50/products/numbers?q=A` 返回 200 而非 500。

### 文件包 PKG-document-crit → Subagent A2
**Files:** `app/routers/document.py`
- [x] **P4-01（C2）** `document.py` `_doc_to_dict`（约 :118-151）：iteration 的 `attachedFiles` 硬编码 `[]` → 查询 `documentiteration_binres` + `binaryresource` 填充（复用同文件 `update_iteration` 约 :499-517 的查询模式）。DB 核实 `\d documentiteration_binres` `\d binaryresource`。验证：GET 有附件的文档 iteration，attachedFiles 非空。

### 文件包 PKG-workspace-crit → Subagent A3
**Files:** `app/services/workspace_deletion.py`、`app/routers/workspaces.py`
- [x] **P5-01（C3）** `workspace_deletion.py` `cascade_delete_workspace`：在删 workspace 本身之前补 folder 清理——先 `UPDATE folder SET parentfolder_completepath=NULL WHERE parentfolder_completepath=:ws OR parentfolder_completepath LIKE :like`，再 `DELETE FROM folder WHERE completepath=:ws OR completepath LIKE :like`（`:like`=`ws/%`）。对齐 Java `WorkspaceDAO.removeWorkspace`。DB 核实 `\d folder`（列 `completepath`/`parentfolder_completepath`）。
- [x] **P5-02（C4）** `workspaces.py` 顶部补 import：`from pathlib import Path`、`from app.core.config import settings`、`indexer_manager`（延迟/顶层导入，按现有服务模块路径核实）。消除 disk_usage_stats(:148)/reindex_workspace(:241)/create_workspace(:422) 的 NameError。验证：三端点首次调用不再 NameError。

### 文件包 PKG-change-workflow-crit → Subagent A4
**Files:** `app/routers/change_common.py`、`app/routers/workflow.py`
- [x] **P6-02（C5）** `change_common.py` `_set_affected_documents`（约 :226-230）：去掉硬编码 `iteration=1`，改为查 `MAX(iteration)`（对齐同文件 `_set_affected_parts`）或从 body 取 iteration。DB 核实 `changeissue_affected_document`/`changeorder_affected_document`/`changereq_affected_document` FK→`documentiteration`。
- [x] **P6-03（C6）** `workflow.py` `get_instance`/`get_workspace_workflow`（约 :44-50）：填充 WorkflowActivityDTO 的 `complete`（status=2 计数）/`inProgress`（status=1）/`toDo`（status=0）/`stopped`（workflow aborted）/`relaunchStep`（查 activity_relaunch 表）。对齐 Java `ActivityDozerConverter`。
- [x] **P6-09（顺带 HIGH）** `workflow.py` `get_instance`（约 :51-57）：`currentStep` 不再硬编码 0，按 Java `WorkflowDTO.getCurrentStep()`（遍历 activities 累加 isComplete）计算。

### 主 agent 批 1 收尾
- [x] 逐包 code review（diff 对照规格 + DB 真值）。
- [x] 部署 back-py（rebuild 镜像 + recreate，health 200）。
- [x] 在线 smoke（GD50，test1 JWT）：CI 搜索 200 ✅；文档 GET 200 且 attachedFiles 从 DB 填充（GD50 无附件行故为空）✅；seed 临时 ws+2 folder→DELETE 204→folder/workspace 残留 0 ✅；disk-usage-stats 200（原 NameError）✅；P6-02/P6-03/P6-09 因 GD50 无 workflow/change-iteration 数据，由 code review + pytest 覆盖。
- [x] `pytest -q --ignore=tests/test_vault.py` = 279 passed / 1 skipped（= 282 基线减 3 个 ignore，无新增 fail）。
- [x] commit `c27547c` + 更新 CHANGELOG/REMINDERS + 勾除本文件。

---

## 批次 2：P1 权限/安全 HIGH（4 并行 subagent，文件不相交）

**越权访问、信息泄露、级联删除保护缺失、FK 500——安全优先级最高，紧随 CRITICAL。**

### 文件包 PKG-document-perm → Subagent B1
**Files:** `app/services/document_manager.py`、`app/routers/document.py`、`app/routers/folders.py`
- [x] **P4-02** `document_manager.py` `release`（约 :753）：开头补 `check_write_access`（对齐 Java `checkDocumentRevisionWriteAccess`）。
- [x] **P4-04** `move_document`（`document.py:726` + service）：补 write access 检查。
- [x] **P4-05** `delete_folder`（`document_manager.py:1079` + `folders.py:117`）：补 `is_home`/`is_root`/`is_another_user_home` 保护（对齐 Java NotAllowedException21）。
- [x] **P4-06** `move_folder`（`folders.py:76`）：补 home/root + 跨工作区目标验证。
- [x] **P4-07** `delete_template`（`document_manager.py:1166`）：`DELETE FROM acl` 前先删 `acluserentry`+`aclusergroupentry`（DB 确认两 FK 无 CASCADE）。
- [x] **P4-08** `update_doc_acl`（`document.py:711`）：补 `hasEntries`→removeACL 分支 + admin/author 权限检查。
- [x] **P4-09（DTO）** `inverse_path_link`（`document.py:464`）：补 partLinksList/serialNumber（findProductByPathMaster + decodePath）。

### 文件包 PKG-part-perm → Subagent B2
**Files:** `app/services/product_manager.py`
- [x] **P1-04** `get_latest_revision`（约 :87-97）：补 `check_read_access`（对齐 Java `getLatestPartRevision`→canAccess→hasPartRevisionReadAccess），无权限 403。修复信息泄露。

### 文件包 PKG-admin-perm → Subagent B3
**Files:** `app/routers/admin.py`
- [x] **P5-07** `get_platform_options`（约 :263）补 `current_user` 参数 + `_require_admin`；`get_index`（约 :409）补认证 + `_require_admin`（对齐 Java `AdminResource` 类级 `@RolesAllowed(ADMIN_ROLE_ID)`）。

### 文件包 PKG-membership-dto → Subagent B4
**Files:** `app/routers/workspace_memberships.py`、`app/routers/user_groups.py`
- [x] **P5-03** `remove_from_group`（`workspace_memberships.py:149`）：返回被操作的 group（按 gid 查）或 204，而非 `list_groups()[0]`。
- [x] **P5-04** `setUserAccess`（`workspace_memberships.py:235`）：返回 UserDTO；membership 为 null → 400。
- [x] **P5-06** `my_memberships`（`workspace_memberships.py:61`）：返回单个 WorkspaceUserMemberShipDTO（非列表）；移除 Java 不存在的 `permission` 字段。
- [x] **P5-05** `setGroupAccess`（`user_groups.py:141`）：返回 WorkspaceUserGroupMemberShipDTO（workspaceId/memberId/readOnly）。

### 主 agent 批 2 收尾
- [x] 逐包 review + 部署（rebuild+recreate, health 200）。主 agent 纠正 B2 建议的错误 admin 检查（account.isadmin 不存在→改用 usergroupmapping groupname='admin'），并在 part.py 接线 P1-04。
- [x] smoke：get_platform_options/get_index 非 admin→403 ✅；latest-revision authed 200 / noauth 401 ✅；my_memberships 返回单对象 ✅；update_doc_acl 空 entries→204 ✅；acl_factory/decode_path 签名 + prdinstiteration_pathdatamstr 列名核实通过。
- [x] `pytest` 279 passed/1 skipped（无新增 fail）。commit c-batch2。更新文档 + 勾除。

---

## 批次 3：P2 workflow/change/baseline/effectivity HIGH（4 并行 subagent，文件不相交）

### 文件包 PKG-task-holder → Subagent C1
**Files:** `app/services/task_manager.py`
- [x] **P6-01** `process_task`（约 :215-270）：补 holder 特定副作用——审批/拒绝时按 holderType 发通知（`sendApproval`/state notification）+ checkedOut 防护（被签出时拒绝审批，对齐 Java `checkTaskAccess`）。**注意：核心状态机已对齐，勿重复实现；Java 无显式 releaseDocument（靠 JPA 状态机），不要臆造。**

### 文件包 PKG-workflow-model → Subagent C2
**Files:** `app/services/workflow_manager.py`、`app/routers/workflow_models.py`
- [x] **P6-04** `create_model`/`update_model`：处理 `ActivityModelDTO.relaunchStep`，写入 `activitymodel_relaunch` 表（DB 核实表结构）；对齐 Java `extractActivityModelFromDTO`。
- [x] **P6-08** `instantiate_workflow`（约 :406）：补审批通知邮件（遍历 running tasks worker，对齐 Java `notifier.sendApproval`）；若 notifier 无接口则实现最小接口。
- [x] **P6-06** `workflow_models.py` `update_model_acl`（约 :133）：返回 204 无 body（Java noContent）。

### 文件包 PKG-milestone-org → Subagent C3
**Files:** `app/routers/milestones.py`、`app/routers/organizations.py`
- [x] **P6-07** `milestones.py` `set_milestone_acl`（约 :131）：返回 204 无 body（Java noContent）。
- [x] **P8-02** `organizations.py` `move_member`（约 :195-237）：补 `direction` 查询参数，实现 `moveMemberDown`（与后一成员交换序号），无效 direction → 400。对齐 Java `moveMember`。

### 文件包 PKG-baseline-effectivity → Subagent C4
**Files:** `app/routers/effectivity.py`、`app/routers/product_baselines.py`
- [x] **P3-02** `effectivity.py` `_effectivity_to_dto`（约 :31-64）：设 `"configurationItemKey":{"workspace":...,"id":...}` 嵌套对象（替代扁平 configurationItemNumber/workspaceId）；对齐 Java EffectivityDTO。
- [x] **P3-03** `effectivity.py` `put_effectivity`（约 :183-214）：按 `eff.dtype` 分派校验——Date→startDate/Serial→startNumber/Lot→startLotId 非空（否则抛 CreationException，对齐 Java updateEffectivity）。参照同文件已修的 POST create_effectivity。
- [x] **P3-01** `product_baselines.py` `_bl_summary_dict`/`_bl_detail_dict`（约 :60-98）：`substituteLinks`/`optionalUsageLinks` 改为查 `productbaseline_substitutelink`/`productbaseline_optionallink` 输出**路径字符串数组**（对齐 Java Set<String>）；schema 由 List[dict] 改 List[str]（参照第一轮 config 域修复）。

### 主 agent 批 3 收尾
- [x] 逐包 review + 部署。**主 agent 修复 C1 task_manager.py 缩进回归**（`if not skip_potential_worker_check:` 下的 `_is_potential_worker` 被误 dedent → 语法错误），并应用 C4 的 2 处 schema List[dict]→List[str]（product/product_baseline.py + product/__init__.py）。notifier 无 sendApproval → P6-08/P6-01 通知留 TODO。
- [x] 对拍：activitymodel_relaunch 列名（activitymodel_id/relaunchactivitymodel_id）+ productbaseline_substitutelink 列名核实；baseline list/effectivity 无数据故仅结构核对；move_member 因 test1 非组成员先 403（access 前置检查，direction=400 逻辑经 code review）。
- [x] `pytest` 279 passed/1 skipped（无新增 fail）。commit（分域）。更新文档 + 勾除。

---

## 批次 4：P3 products 结构/实例 + query HIGH（3 并行 subagent，文件不相交）

### 文件包 PKG-product-structure → Subagent D1
**Files:** `app/services/product_structure.py`、`app/routers/product_instances.py`
- [x] **P2-01** `delete_instance`（约 :822-826）：删 `productinstanceiteration` 前先清 7 张子表 `prdinstiteration_attribute`/`_binres`/`_documentlink`/`_p2plink`/`_pathdatamstr`/`prdinstanceiteration_optlink`/`_sublink`（+孤儿 instanceattribute/documentlink）。DB 逐一核实 FK。对齐 Java `ProductInstanceMasterDAO`。
- [x] **P2-05** `_check_has_path_data`（约 :388-406）：CI ID 含连字符时定位错——改用 `re.search(r'[-](?:u|s)\d+', comp_path)` 定位首个 `-u`/`-s` 构造 db_path（当前 `find("-")` 命中 CI 内连字符）。
- [x] **P2-06** `product_instances.py`（约 :147-150）+ `product_structure.parse_config_spec_str`（约 :123）：实现 `pi-{serial}` 完整 configSpec 解析（查 baseline→ResolvedCollectionConfigSpec→ProductBaselinePSFilter），去掉降级为 "latest"。对齐 Java `PSFilterManagerBean.getProductInstanceConfigSpec`。

### 文件包 PKG-products-pathdata → Subagent D2
**Files:** `app/routers/products.py`、`app/services/products/path_data_service.py`
- [x] **P2-04** `products.py` `get_product_instance`（约 :383）：每个 iteration 补 11 字段（substituteLinks/optionalUsageLinks/substitutesParts/optionalsParts/pathDataMasterList/pathDataPaths/pathToPathLinks/basedOn/instanceAttributes/linkedDocuments/attachedFiles）。对齐 Java `getProductInstance`。
- [x] **P2-03** `path_data_service.py` `_build_master_dict`（约 :443-451）：填充 `partLinksList`（decodePath）/`partAttributes`/`partAttributeTemplates`（PSFilter+partIteration）。对齐 Java `getPathData`。

### 文件包 PKG-importer → Subagent D3
**Files:** `app/services/importer.py`
- [x] **P7-01** `import_into_path_data`（约 :270-282）：移植 Java `doPathDataImport`+`createOrUpdatePathData`+`bulkPathDataUpdate`（Excel 解析→createOrUpdate PathData→批量写迭代属性）。
- [x] **P7-03 附带独立 bug** `import_into_parts`（约 :217）：返回真实 errors 列表（当前硬编码 `errors:[]` 丢弃 checkout 失败错误）；并将循环内 `db.commit()`（约 :209）移出循环做单次批量 commit（降低半成品风险）。

### 主 agent 批 4 收尾
- [x] 逐包 review + 部署。主 agent 更新 test_import_path_data_stub → 断言不再是 stub（P7-01 已实现）。D1 P2-06 为 Tier-2 实现（baseline 迭代映射，未做 optional/substitute 过滤）；D2 P2-04/P2-03 直接可查字段全填 + decode 字段异常安全。
- [x] smoke：product structure filter latest/released/wip 全 200（P2-05 含连字符 CI ACLCI-45ECFC 正常）；delete_instance 不存在 SN→404（非 500，路由已接线）。P2-01/P2-04 因 GD50 无 productinstancemaster 数据，由 code review（7 FK 子表 + 列名全核实）+ pytest 覆盖。
- [x] `pytest` 279 passed/1 skipped（test_import_path_data_stub 已更新）。commit（分域）。更新文档 + 勾除。

---

## 批次 5：MED/LOW 收尾（按域报告分包）

**改动模式一致（状态码 204、DTO 字段补齐/null 语义、死代码清理、幂等），高度可并行。按文件分包，逐文件对照各域报告 `docs/migration/audit-round2/0X-*.md` 的 MED/LOW 清单。**

主要项（非穷举，以域报告为准）：
- **状态码 204 对齐**：P2-12、P3-04、P3-05、P8-03（acknowledge）等 delete/PUT-ACL 端点。
- **DTO 字段/null 语义**：P1-06/07/10、P2-13、P4-10/15/16、P5-08~11、P6-11（assignedGroups）/P6-12（NOT_TO_BE_DONE）、P8-08。
- **边界/功能**：P4-11/12（create 忽略 acl/roleMapping/attributesLocked）、P4-13（list_templates NameError 边界）、P4-03（undo_checkout 补 admin 特权分支）、P7-04~08（Excel/导出格式）、P6-10/P6-13/P8-05/P8-06（补写权限/组检查）。
- **事务/中间件**：P4-14（循环内 commit）、P8-07（UserLanguageMiddleware 连接复用）。
- **死代码/风格/幂等**：P3-08（document_baseline_manager 用不存在列）、P7-10（importer docstring 过时）、P7-02（BOM stub 加注释说明 Java 亦无实现）、P8-01（layer marker 删除顺序，或标注为对齐 Java 死代码）、P5-13（权限函数重复 5 处）、P6-14（SELECT * 索引取值）、P6-15（无界缓存）、P7-12（import 子表幂等）。

### 主 agent 批 5 收尾
- [x] 按域报告逐文件包并行修（2 波：域1-4 / 域5-8）→ review → 部署 → 全量 pytest 无新增 fail（279 passed/1 skipped，含 test_i18n_bypass）→ 抽样对拍 → commit → 更新文档。
  > **实际修复 40 MED 中的绝大多数**（部分为 no-op/注释标注：P2-09 已对齐、P3-06 已存在、P7-05/P7-07/P8-07 加注释、P2-10 vault 路径已对齐）。
  > **主 agent 纠正的 subagent 隐患**：① 域1 P1-06/P1-07 null 语义改动经 Payara 复核后回退（front-compat 风险、低价值）；② 域4 document_templates.py dict 推导式语法错误（2 处）修复；③ **域1 P1-05/P1-03 硬编码 `raise HTTPException` 违反 i18n 约定**（P1-03 甚至替换掉了原有领域异常）→ 改回 NotAllowedException/PartMasterNotFoundException/PartIterationNotFoundException（test_i18n_bypass 因用位置参数而漏检，主 agent 手工 grep 揪出）；④ 域1 P1-09 越界改了 product_manager.py（无并发冲突，改动正确）。
  > commits: 批5波1、`part.py i18n fix`、批5波2。

> **🎉 audit-round2 批次 1~5 全部完成**：6 CRITICAL + 29 HIGH + 40 MED 已处理；24 LOW 未列入本轮（用户指定只修到 MED）。

---

## 批次 6：邮件通知族全量迁移（planned，用户选 B — 对齐 Payara `NotifierBean`）

> **来源**：P6-08/P6-01 审计发现的审批邮件缺口，深查确认为**系统性缺口**（详见 `docs/migration/loose-ends.md` 第八节）。Payara `NotifierBean` 经 `mail/docdokuSMTP`→MailHog 真实发信；Python `app/services/notifier.py` 已有 `_send_email`(smtp:1025 MailHog) 基础设施，仅迁移了 bulk-indexation。**决策：整族补全，彻底对齐 Payara（非仅审批）。**
> **状态：待实施**（本次仅登记计划，未写代码）。

### 待实现方法 + 触发点接线（对照 `NotifierBean` public API）
- [ ] **NB-1 sendApproval**（doc/part/workspaceWorkflow）：`workflow_manager.instantiate_workflow`（P6-08 锚点）+ `task_manager.process_task` approve/reject-relaunch（P6-01 锚点）；收件人 = running task worker email。
- [ ] **NB-2 sendStateNotification**：文档审批推进且 step 变化 → 发订阅者。
- [ ] **NB-3 sendIterationNotification**：新迭代 checkin（document_manager / product_manager）→ 发迭代订阅者。
- [ ] **NB-4 sendTagged / sendUntagged**（doc+part）：打/去标签 → 发标签订阅者（`tagusersubscription`/`tagusergroupsubscription`）。
- [ ] **NB-5 sendPasswordRecovery**：`auth` 恢复端点（P8-04 已写 `passwordrecoveryrequest` token，补发信）。
- [ ] **NB-6 sendWorkspaceDeletionNotification / ...ErrorNotification**：`workspace_deletion` 成功/失败。
- [ ] **NB-7 send{Part,Document,Workspace}WorkflowRelaunchedNotification**：拒绝 + relaunch 后。
- [ ] **NB-8 sendWorkspaceIndexationSuccess / Failure**：单工作区重建索引（bulk 版已迁移）。
- [ ] **NB-9 sendCredential**：新建账户下发凭据。

### 文件包建议（供后续编排；跨批次可与既有文件重叠，串行执行）
- PKG-notifier（核心）：`app/services/notifier.py`（新增各 send_* 方法 + i18n 模板）
- PKG-wire-workflow：`app/services/workflow_manager.py`、`app/services/task_manager.py`（NB-1/NB-7）
- PKG-wire-content：`app/services/document_manager.py`、`app/services/product_manager.py`（NB-3/NB-4）
- PKG-wire-misc：`app/routers/auth.py`（NB-5）、`app/services/workspace_deletion.py`（NB-6）、`app/services/indexer_manager.py`（NB-8）、`app/services/account_manager.py`（NB-9）

### 约束
- 复用 `notifier._send_email`（MailHog）；正文对齐 Java `sendXxxToUser` 模板 + i18n；**全部 best-effort（try/except+log，不阻断主流程）**，与 Payara `@Asynchronous`/吞异常语义一致。
- 验证：触发后查 MailHog（:8003）收件箱；pytest 无新增 fail。

### 主 agent 批 6 收尾（待办）
- [ ] 派 subagent 实现 + 接线 → review → 部署 → pytest + MailHog 验证 → commit → 更新文档。

---

## 附录 A：全局文件所有权矩阵（防重叠证明）

**规则：同一批次列内，每个文件只出现在一个 subagent 行。跨批次可重复。**

| 文件 | 批1 | 批2 | 批3 | 批4 |
|------|:--:|:--:|:--:|:--:|
| routers/products.py | A1 | | | D2 |
| routers/document.py | A2 | B1 | | |
| services/workspace_deletion.py | A3 | | | |
| routers/workspaces.py | A3 | | | |
| routers/change_common.py | A4 | | | |
| routers/workflow.py | A4 | | | |
| services/document_manager.py | | B1 | | |
| routers/folders.py | | B1 | | |
| services/product_manager.py | | B2 | | |
| routers/admin.py | | B3 | | |
| routers/workspace_memberships.py | | B4 | | |
| routers/user_groups.py | | B4 | | |
| services/task_manager.py | | | C1 | |
| services/workflow_manager.py | | | C2 | |
| routers/workflow_models.py | | | C2 | |
| routers/milestones.py | | | C3 | |
| routers/organizations.py | | | C3 | |
| routers/effectivity.py | | | C4 | |
| routers/product_baselines.py | | | C4 | |
| services/product_structure.py | | | | D1 |
| routers/product_instances.py | | | | D1 |
| services/products/path_data_service.py | | | | D2 |
| services/importer.py | | | | D3 |

**每列校验**：批1(A1,A2,A3,A4 无交)、批2(B1,B2,B3,B4 无交)、批3(C1,C2,C3,C4 无交)、批4(D1,D2,D3 无交)。✅ 全批次文件不相交。跨批次重复：products.py(批1/批4)、document.py(批1/批2)——串行无冲突。

---

## 附录 B：主 agent 每批标准流程（SOP）

1. 派本批 subagent（含：文件包清单 + 对应问题规格 + `full-audit-checklist.md` + 对应域报告路径 + 「只写认领文件、禁验证/commit/派生/skill」硬约束）。
2. 回收后逐包 code review：diff 对照规格 + DB 真值 + 相邻文件接口一致性；警惕 subagent 引入的 GLB 路径/删除顺序类隐患（参照第一轮 X-6/delete_baseline 教训）。
3. 部署 back-py。
4. 验证：`pytest -q`（对齐 282 基线，无新增 fail）+ 本批针对性在线 smoke/Payara 对拍。涉 500 的 CRITICAL 在 GD50 有数据环境实测。
5. 若失败：主 agent 亲自修或带 review 意见重派对应 subagent。
6. 全绿后 commit（Conventional Commits，按域拆原子 commit）。
7. 更新 `docs/CHANGELOG.md` + `docs/REMINDERS.md` + 勾除本文件 + 对应 `docs/migration/audit-round2/*.md` 标注已修。
