# 迁移代码审计（第4轮）修复实施计划（FIX-PLAN — audit-round4）

> 对应审计报告：`docs/migration/audit-round4/00-index.md` + 8 域报告
> 审计基准：**第3轮大重构（分支 `fix/audit-remediation`）之后**的代码
> 修复原则：**无条件对齐 Payara 后端**（以 Java 源码为功能对照基准，information_schema 为 schema 真值源，Payara 实际响应为格式真值源）
> 修复分支：延续 `fix/audit-remediation`

**Goal:** 修复本轮 2 CRITICAL + 13 HIGH（+ 视情况 MED），重点消除 2 个必 500 写入路径 bug + 权限系统性缺口，同时不破坏第3轮已闭环成果、pytest 基线保持 **282 passed / 1 skipped**。

**Scope 决策（✅ 用户已确认 2026-07-12）：** 覆盖 **2 CRITICAL + 13 HIGH + 16 MED**；**22 LOW 不列入**（延续"修到 MED"惯例）。**P7-15（import 事务边界）本轮执行**（用户确认）。**已知计划外项**（P6-01/P6-08 审批邮件、P5-12 put_index ES 桩、P5-21 delete_account 级联不全）不在本轮，归入邮件族/后续排期。

---

## 全局约束（务必写进每个 subagent 的 prompt）

- **DB 真值源唯一**：任何表名/列名修改前须 `docker exec docdoku-plm-docker-db-1 psql -U changeit -d docdokuplm -c "\d 表名"` 核实。
- **Java 对齐**：每处"Java 如何做"须打开对应 Java 文件按方法名确认，不凭印象/不信旧行号。
- **subagent 铁律**：只读 Java + 只写自己认领的 Python 文件；**禁止** `pytest`/`git`/`docker`/改其他文件/派生子 agent/调用 skill/todo。
- **主 agent 独占**：验证、部署（rebuild back-py）、commit、跨文件重构决策、CRITICAL 修复的造数据复测。
- **异常一致性**：service 层抛领域异常（`app/core/exceptions.py`），**禁止**硬编码 `raise HTTPException`（路由层需要特殊响应头的除外，如 share.py）。
- **权限修复统一入口**：admin 检查用 `core/deps.py` 的 `require_global_admin`/`require_workspace_admin`（Depends）或 router 内 `_check_workspace_admin`；写权限用 `services/factory/acl_factory.py` 的 `check_write_access(db, acl_id, login, is_admin, workspace_id=ws)`。
- **提交信息**：Conventional Commits（`fix:` / `refactor:`）。
- **pytest 基线**：`venv/bin/python -m pytest -q` → 改动不得引入新 fail（基线 282 passed / 1 skipped）。
- **CRITICAL 复测**：空库测不到（清单#18），主 agent 须造数据在 GD50 复测（P2-14 造 PathData、P3-11 造含 substituteLinks 的基线）。

---

## Batch 总览

| Batch | 主题 | 并行度 | 依赖 | 核心产出 |
|-------|------|:--:|------|------|
| **1** | 2 CRITICAL 必 500 修复 | 2 subagent | 无 | PathData INSERT 列名 + 基线链接写入表修正，造数据复测 |
| **2** | 权限系统性缺口（6 项 HIGH） | 4 subagent | 无 | tags/obsolete/用户组/stats/PathData 导入统一补权限 |
| **3** | 其余功能 HIGH（7 项） | 3 subagent | Batch 1 | UPSERT→500、holderType、notification、硬编码异常、configSpec、newVersion |
| **4** | MED 收尾（16 项）+ import 事务 | 5 subagent | Batch 2~3 | 状态码/DTO 字段/死代码/幂等/桩补全 + P7-15 事务边界 |

## 执行结果 (2026-07-12) ✅ 全部完成

| Batch | 状态 | commit | 效果 |
|-------|:--:|--------|------|
| **1** | ✅ 完成 | `0d087a1` | P2-14 列名 + P3-11 基线链接写表；GD50 造数据复测（PathData 201 / baseline 201 links round-trip） |
| **2** | ✅ 完成 | `84d9229` | P1-13/P4-NEW1/2/3/P5-19/P5-07-REG/P7-14 权限补齐；smoke: 非admin→403, ws-admin→201, global-admin→200 |
| **3** | ✅ 完成 | `c69d251` | P5-18(→400)/P6-17/P8-11(通知非空)/P6-18/P2-15/P1-14/P8-12/P1-12/P2-06 |
| **4** | ✅ 完成 | `d46e7ea` | P2-12/P5-16(→204)/P5-08(去admin字段,含schema)/P5-20/P3-03/P3-10/P8-06/P3-12/P3-09/P7-12/P4-NEW4/P7-15 事务 |

**主 agent 修正的 subagent 隐患**：
- Batch4-A 把 P8-03（LOW，超范围）改成 204 破坏 `test_acknowledge_notification` → 回退为 200+DTO（P8-03 属 LOW，不在本轮 scope）。
- Batch4-B 只改了 workspaces.py 的 `_row_to_dict`，但 P5-08 根因在 **WorkspaceDTO schema 声明了 `admin` 字段**（extra='forbid'）+ admin.py `_workspace_to_dict` 也返回 `admin`/`creationDate` → 主 agent 补删 schema 的 `admin` 字段 + admin.py 两个多余字段（否则 admin 端点 ResponseValidationError 500）。

**未修（保留，均已在报告说明）**：
- **P2-08**（linkType PSFilterVisitor 完整重构）——风险高、影响面大，保留最小实现。
- **P1-06**（status NULL→"WIP"）——保守保留，需 Payara 对拍 null 序列化后再定（当前 DB 无 NULL status 记录）。
- **P8-03**（acknowledge 204）——LOW，超本轮 scope + 有测试依赖。
- **22 LOW + 已知计划外项**（邮件族 P6-01/P6-08、put_index ES 桩 P5-12、delete_account 级联 P5-21）。

**验证**：每批 rebuild/hot-copy 部署 + pytest（全程 **282 passed / 1 skipped**，零回归）+ 针对性 smoke + Payara 对拍。最终 `docker build` 持久化镜像 + `compose up --force-recreate`，服务健康（login 200）。

---


## Batch 1：2 个 CRITICAL 必 500 修复（最高优先）

**Why first:** 两处写入路径 100% 500，功能完全不可用；修复明确（列名/写入表），风险低但影响大。

### 文件包 PKG-pathdata → Subagent A
**Files:** `app/services/products/path_data_service.py`

- [ ] **P2-14**：`_attach_master_to_instance`（:316-323）的 INSERT `prdinstiteration_pathdatamstr`，列名 `iteration` → `prdinstanceiteration_iteration`。
  - psql `\d prdinstiteration_pathdatamstr` 确认 PK 复合列为 `(prdinstanceiteration_iteration, prdinstancemaster_serialnumber, configurationitem_id, workspace_id, pathdatamaster_id)`。
  - 核对同文件其他 INSERT/SELECT（`product_instance_manager.py:364` 用的是 `prdinstanceiteration_iteration`）保持一致。
  - 全文件 grep 是否还有其他误用 `iteration` 列名写该表的地方。

### 文件包 PKG-baseline-create → Subagent B
**Files:** `app/services/product_structure.py`（仅 `create_baseline` :905-966 段）

- [ ] **P3-11**：create_baseline 的 substitute_links/optional_usage_links 写入逻辑。
  - 入参是**路径字符串**（`Set[str]`，来自 `spec.retained_substitute_links`），不是 dict——移除 `sl.get(...)`。
  - substitute_links → `INSERT INTO productbaseline_substitutelink (productbaseline_id, substitutelinks) VALUES (:pbid, :path)`（psql `\d` 确认列名 `substitutelinks` varchar(255)）。
  - optional_usage_links → `INSERT INTO productbaseline_optionallink (productbaseline_id, optionalusagelinks) VALUES (:pbid, :path)`（psql `\d productbaseline_optionallink` 确认列名）。
  - 删除现有写 `partsubstitutelink` / `UPDATE partusagelink SET optional` 的错误逻辑。
  - 对照 Java `ProductBaselineManagerBean.java:102-167` `baseline.addSubstituteLink(pathStr)`/`addOptionalUsageLink(pathStr)` 的 `@ElementCollection` 语义确认。
  - ⚠️ 注意 `product_structure.py` 是大文件（1548 行），只改 create_baseline 段，勿动 `_resolve_pi_config_spec`（Batch 3 处理）。

### 主 agent Batch 1 收尾
- [ ] rebuild+recreate back-py
- [ ] **P2-14 复测**：GD50 造一个产品实例 → POST 创建 PathData iteration → 确认 200（无 `column "iteration" does not exist`）
- [ ] **P3-11 复测**：GD50 造含非空 substituteLinks 的 POST 基线创建 → 确认 200 + 查 `productbaseline_substitutelink` 有正确行；再 GET 基线详情确认 substituteLinks 回读正确
- [ ] pytest 无新增 fail
- [ ] commit（2 个原子：`fix: correct prdinstiteration_pathdatamstr iteration column (P2-14)` / `fix: write baseline substitute/optional links to correct tables (P3-11)`）

---

## Batch 2：权限系统性缺口（6 项 HIGH）

**Why second:** 第3轮统一 Depends/迁移 service 时系统性遗漏"非核心 CRUD"端点权限检查，属安全漏洞。统一补齐。**根因共性**：写/admin 检查缺失，修复模式统一。

### 文件包 PKG-perm-tags → Subagent A
**Files:** `app/services/product_manager.py`（仅 remove_tag :1166）、`app/routers/part.py`（remove_tag handler）

- [ ] **P1-13**：`remove_tag` 补 `current_user_login` 参数 + `check_write_access(db, pr.acl_id, current_user_login, False, workspace_id=ws)`，对齐同文件 `add_tag`(:1142)/`set_tags`(:1118)。router 传 `current_user.login`。
  - 对照 Java `PartResource.java` removeTag → `productService.removeTag()` throws AccessRightException。

### 文件包 PKG-perm-doc → Subagent B
**Files:** `app/services/document_manager.py`（mark_obsolete :899、set_tags :970、add_tag :987、remove_tag :1004、create_document :60）

- [ ] **P4-NEW1**：`mark_obsolete`（:899）在 `get_revision` 之后、status 检查之前补 `check_write_access`（对齐 Java `DocumentManagerBean.java:1766` checkDocumentRevisionWriteAccess，NotAllowedException65）。
- [ ] **P4-NEW2**：`set_tags`/`add_tag`/`remove_tag`（:970/:987/:1004）三方法入口各补 `check_write_access(db, pr.acl_id, user_login, False, workspace_id=ws)`（对齐 Java saveTags/removeTag → checkDocumentRevisionWriteAccess）。需给缺参数的方法补 `user_login`，router 传入。
- [ ] **P4-NEW3（MED，顺带）**：`create_document`（:60）入口补 `check_write_access(db, None, user_login, False, workspace_id=ws)`（对齐 Java createDocumentMaster→checkWorkspaceWriteAccess）。

### 文件包 PKG-perm-usergroup → Subagent C
**Files:** `app/routers/user_groups.py`、`app/routers/workspace_memberships.py`

- [ ] **P5-19**：7 个端点补 `_check_workspace_admin(db, ws, current_user)`（对齐 Java `UserManagerBean` 各写操作首行 `checkAdmin`）：
  - `user_groups.py`：create_group(:33)、delete_group(:43)、enable_group(:58)、disable_group(:72)、set_group_access(:84)
  - `workspace_memberships.py`：add_user(:77)、remove_from_workspace(:92)
  - 参照同文件已正确加检查的 enable-user/disable-user/set_user_access/set_admin 写法。

### 文件包 PKG-perm-admin-import → Subagent D
**Files:** `app/routers/admin.py`、`app/routers/accounts.py`、`app/services/importer.py`

- [ ] **P5-07-REG**：admin stats + index 8 端点统一加 `Depends(require_global_admin)`（对齐 Java `AdminResource.java:62-63` 类级 `@RolesAllowed(ADMIN_ROLE_ID)`）：
  - `admin.py`：disk-usage-stats(:153)、users-stats(:160)、documents-stats(:167)、products-stats(:174)、parts-stats(:181)、index/{ws}(:190)
  - `accounts.py`：accounts-stats(:57)、workspace-stats(:64)
- [ ] **P7-14**：`import_into_path_data`（:378-379 TODO 处）补实例级 canWrite 检查——Phase1 循环调用 `product_instance_manager.canWrite(db, ws, ci_id, sn)`，无权限时跳过该行 + errors 追加 AccessRightException（对齐 Java `ImporterBean.java:527`）。
  - 先确认 `product_instance_manager` 是否已有 canWrite 方法，无则参照 Java 逻辑实现。

### 主 agent Batch 2 收尾
- [ ] rebuild+部署；pytest 无新增 fail
- [ ] smoke：非授权用户对上述端点应 403（对拍 Payara `:8005`）；授权用户正常 200/204
- [ ] commit（分域：tags 权限 / 文档权限 / 用户组权限 / admin+import 权限）

---

## Batch 3：其余功能 HIGH（7 项）

**依赖 Batch 1**（product_structure.py 已被 Batch 1 改过 create_baseline，本批改 `_resolve_pi_config_spec`，避免同文件并发）。

### 文件包 PKG-workspace-fix → Subagent A
**Files:** `app/services/user_manager.py`（set_user_access/grantUserAccess :375）、`app/routers/workspace_memberships.py`（若 Batch 2 未占，本批不重复占，见附件 A）

- [ ] **P5-18**：`set_user_access`（:375-391）UPSERT → 改 SELECT-then-UPDATE：先 `SELECT 1 FROM workspaceusermembership WHERE ...` 确认成员存在；不存在 → 抛领域异常映射 400（对齐 Java `UserManagerBean.java:250-257` loadUserMembership 返回 null→400）；存在 → 仅 `UPDATE readonly`（移除 `ON CONFLICT ... INSERT` 分支）。
  - ⚠️ 与 Batch 2 PKG-perm-usergroup 都涉 `workspace_memberships.py`——**本项只改 `user_manager.py` service 层**，router 层的 add-user 权限由 Batch 2 处理；若行号冲突，主 agent 串行执行（Batch 2 先）。

### 文件包 PKG-task-notif → Subagent B
**Files:** `app/services/task_manager.py`、`app/services/notification_manager.py`

- [ ] **P6-17**：`_resolve_holder`（:46/:52）+ `_relaunch_workflow`（:566/:582）holderType 统一改复数：`"part"`→`"parts"`、`"workspace-workflow"`→`"workspace-workflows"`（对齐 Java `TaskManagerBean.java:142/151/160`）。全文件 grep 所有引用点一并改（约 12 处），确认 get_assigned_tasks/get_task_dto/process_task 返回一致。
- [ ] **P8-11**：`list_for_user`（:25-31）移除 `ackauthor_login == login` 过滤条件（该列是"确认人"，未读通知恒为 NULL）。确认正确的未读过滤语义（impacted_workspace_id + acknowledged=False + 按订阅关系确定收件人，对照 Java 通知嵌入 PartRevisionDTO 的取数逻辑）。
- [ ] **P6-18（MED，顺带）**：`get_assigned_tasks`(:145)/`get_task_dto`(:183) 查 `task_user` 表填充 `assignedUsers`（对齐 Java TaskDTO.assignedUsers）。

### 文件包 PKG-product-exc → Subagent C
**Files:** `app/services/product_manager.py`（retry_conversion :1885、get_leaf_instances :1999、create_new_version :1071、set_new_version_description :1990）、`app/routers/products.py`、`app/routers/part.py`（new_version handler :193）

- [ ] **P2-15/P1-14**：`product_manager.py:1895`（"No native CAD file uploaded"）、`:2007`（"partKey 格式应为..."）硬编码 HTTPException → 改领域异常（WrongInputException / 对应 NotFound），或将格式校验上移路由层（part.py 的 `_split_part_key` 已有）。对照 Java 确认抛哪个异常。
- [ ] **P8-12**：`products.py:111/171/197` 路由层硬编码 HTTPException → ConfigurationItemNotFoundException / ProductInstanceMasterNotFoundException / 直接 `raise`（勿吞 str(e)）。
- [x] **P1-12**：`create_new_version`（:1071）扩展支持 description/workflow_model_id/acl/role_mapping 参数并写到**新版本行**；移除 router 中用旧版本号调 `set_new_version_description` 的逻辑（对齐 Java `PartResource.java:460-489` createPartRevision）。✅ **已完成（2026-07-12）** — 同批修复 apply_acl FK 根本缺陷 + Pydantic WorkflowDTO forward-reference。

### 主 agent Batch 3 收尾（P2-06 主 agent 亲自处理）
- [ ] **P2-06/P2-16**（主 agent 亲改 `product_structure.py:_resolve_pi_config_spec` :1464-1512，避免与 Batch 1 冲突）：ProductInstanceMaster / ProductInstanceIteration 查询补 `configurationitem_id == ci_id`（对齐 Java `ProductInstanceMasterKey(serial, ws, ciId)` 三元组）。
- [ ] rebuild+部署；pytest 无新增 fail
- [ ] smoke：setUserAccess 非成员→400（非 500）；任务 holderType 复数；notification 列表非空（GD50 有 10 条未读）；products 404 语义；newVersion 描述写到新版本
- [ ] commit（分域）

---

## Batch 4：MED 收尾（16 项）

### 文件包 PKG-med-status → Subagent A（状态码/响应形态）
- [ ] **P2-12** product_configurations.py:140 delete_config → 204 no body
- [ ] **P5-16** admin.py:139-146 put_platform_options → 204（Java noContent）
- [ ] **P8-03** notifications.py:23-31 acknowledge → 评估是否对齐 Java 204（低风险，可保留 LOW，主 agent 定）

### 文件包 PKG-med-dto → Subagent B（DTO 字段对齐）
- [ ] **P5-08** workspaces.py:37-44 / admin.py:34-42 WorkspaceDTO 移除多余 `admin` 字段 + 对齐 creationDate
- [ ] **P5-20** workspace_memberships.py:189-195 setUserAccess 返回 UserDTO 移除 extra `membership` 字段
- [ ] **P3-03** effectivity.py:148-182 put_effectivity 强制要求下限字段存在（对齐 Java 始终校验）

### 文件包 PKG-med-baseline → Subagent C（基线/查询）
- [ ] **P3-10** product_baselines.py:237-242 P2P link 详情调 `svc.decode_path()` 填 sourceComponents/targetComponents
- [ ] **P2-08** product_structure.py:1223-1382 linkType 过滤接入 PSFilterVisitor（评估工作量，可降级保留）
- [ ] **P8-06** lov_manager.py:111-124 is_lov_deletable 追加 partiteration_attribute→instanceattribute(dtype='InstanceListOfValuesAttribute') 检查（对齐 Java 第 3 条件）

### 文件包 PKG-med-transaction → Subagent E（import 事务边界，✅ 本轮执行）
**Files:** `app/services/importer.py`（import_into_parts :239-270）、`app/services/product_manager.py`（checkout :426、checkin :463）
- [ ] **P7-15**：让 `import_into_parts` 的 checkout→write→checkin 在单事务内整体成功或回滚（对齐 Java `ImporterBean.bulkPartUpdate` 单 EJB `@TransactionAttribute(REQUIRED)`）：
  - 给 `checkout`(:426)/`checkin`(:463) 增加 `auto_commit: bool = True` 参数，为 True 时保持现有 `db.commit()` 行为（不破坏其他调用方），为 False 时改为 `db.flush()` 交由调用方提交。
  - `import_into_parts` 循环中以 `auto_commit=False` 调用 checkout/checkin，全部成功后由 importer 统一 `db.commit()`；任一零件失败则 `db.rollback()` + errors 记录，不留半成品。
  - ⚠️ grep 所有 checkout/checkin 调用方，确认新增默认参数不改变既有行为（默认 True = 现状）。

### 文件包 PKG-med-cleanup → Subagent D（死代码/幂等/桩）
- [ ] **P3-12** 删除 product_baselines.py:245-271 死代码 `_query_substitute_links`/`_query_optional_links`
- [ ] **P3-09** effectivity_manager.py:92-100 delete_effectivity 删前先查归属 workspace，不匹配抛 EffectivityNotFoundException
- [ ] **P7-12** import_error/import_warning 无主键，complete_import 前 DELETE 幂等
- [ ] **P1-06** part_mapper.py:256 status NULL → 返回 None（不兜底 "WIP"）——注意第2轮批5曾回退过 null 语义，**须先对拍 Payara 确认 Java 序列化 null**再改
- [ ] **P4-NEW4** document_manager.py:2173 build_template_dto attachedFiles 查询填充

### 主 agent Batch 4 收尾
- [ ] 全量 pytest（无回归）+ 抽样对拍 Payara
- [ ] commit（分域）

---

## 附件 A：全局文件所有权矩阵（防批间冲突）

| 文件 | B1 | B2 | B3 | B4 |
|------|:--:|:--:|:--:|:--:|
| `services/products/path_data_service.py` | A | | | |
| `services/product_structure.py`(create_baseline) | B | | | |
| `services/product_structure.py`(_resolve_pi_config_spec) | | | 主agent | |
| `services/product_structure.py`(linkType) | | | | C |
| `services/product_manager.py`(remove_tag) | | A | | |
| `services/product_manager.py`(retry/leaf/newVersion) | | | C | |
| `services/product_manager.py`(checkout/checkin) | | | | E |
| `routers/part.py` | | A | C | |
| `services/document_manager.py` | | B | | D(2173) |
| `routers/user_groups.py` | | C | | |
| `routers/workspace_memberships.py`(router) | | C | | B(:189) |
| `services/user_manager.py`(set_user_access) | | | A | |
| `routers/admin.py` | | D | | A |
| `routers/accounts.py` | | D | | |
| `services/importer.py` | | D | | C+E |
| `services/task_manager.py` | | | B | |
| `services/notification_manager.py` | | | B | |
| `routers/products.py` | | | C | |
| `routers/product_configurations.py` | | | | A |
| `routers/workspaces.py` | | | | B |
| `routers/effectivity.py` | | | | B |
| `services/effectivity_manager.py` | | | | D |
| `routers/product_baselines.py` | | | | C+D |
| `services/lov_manager.py` | | | | C |
| `services/part_mapper.py` | | | | D |
| `routers/notifications.py` | | | | A |

> ⚠️ 冲突点：`product_structure.py`（B1-B 改 create_baseline，主 agent 改 _resolve_pi_config_spec，B4-C 改 linkType）——**主 agent 串行处理该文件的三处，或确保三段行号区间不重叠由不同轮次改**。`workspace_memberships.py`（B2-C 改 router 权限，B3-B 改 :189 DTO）——串行 B2 先。`services/importer.py`（B2-D 改 import_into_path_data canWrite，B4-C 改 is_lov_deletable ❌ 实为 lov_manager，B4-E 改 import_into_parts 事务）——B2-D 与 B4-E 段不同（PathData vs Parts），但同文件须串行（B2 先）。`services/product_manager.py`（B2-A remove_tag、B3-C retry/leaf/newVersion、B4-E checkout/checkin）——三段方法不重叠，但同文件须串行按批次先后改，避免 diff 冲突。

---

## 附件 B：主 agent 每批标准流程

1. 派本批 subagent（含：文件包清单 + 审计报告对应条目 + 全局约束 + Java 对照方法名）
2. 回收后逐包 code review：diff 对照规格 + DB 真值（psql）+ Payara 对拍（`:8009` vs `:8005`）
3. rebuild back-py（`docker build -t docdoku-plm-docker-back-py:latest .` + `docker compose up -d --force-recreate --no-deps back-py`）
4. 验证：`pytest -q`（无新增 fail）+ 本批针对性 smoke（含 CRITICAL 造数据复测）
5. 若失败：主 agent 亲自修或重派
6. 全绿后 commit（Conventional Commits，按域拆原子 commit）
7. 更新 `docs/migration/audit-round4/00-index.md` 进度 + `docs/CHANGELOG.md` + `docs/REMINDERS.md`

---

## 附件 C：严重级 → 批次映射速查

| 批次 | 编号 |
|------|------|
| B1（CRITICAL） | P2-14、P3-11 |
| B2（权限 HIGH） | P1-13、P4-NEW1、P4-NEW2、P5-19、P5-07-REG、P7-14（+ P4-NEW3 MED 顺带） |
| B3（功能 HIGH） | P5-18、P6-17、P8-11、P2-15/P1-14、P8-12、P1-12、P2-06/P2-16（+ P6-18 MED 顺带） |
| B4（MED） | P2-12、P5-16、P5-08、P5-20、P3-03、P3-10、P2-08、P8-06、**P7-15（本轮做）**、P3-12、P3-09、P7-12、P1-06、P4-NEW4、P8-03 |
| 不修（LOW×22） | P1-07/P1-10、P2-13、P3-13、P5-12/P5-21、P6-14/P6-15、P7-05/P7-06/P7-11、P8-07/P8-08/P8-09/P8-10 等 |
| 已知计划外 | P6-01/P6-08（邮件族）、P5-12（ES 桩）、P5-21（级联不全） |
