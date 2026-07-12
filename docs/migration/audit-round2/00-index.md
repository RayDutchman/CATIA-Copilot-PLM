# 迁移代码审计（第二轮）总报告 — 00 Index

> 生成日期：2026-07-12 ｜ 范围：`docdoku-plm-server-py` 全量迁移代码 vs Java/Payara（`docdoku-plm-server`）**代码对比**
> 方法：8 域 explore subagent 并行逐端点对照 Java 源 + information_schema 核实 + GD50 有数据环境验证 → 主 agent 汇总去重定级 → **8 域 subagent 独立复核**（重新定位实际 Python + Payara Java 代码 + DB FK 核实，裁决真实性/降级/证伪）。
> 基准 workspace = GD50 ｜ 只读审计，**未做任何修复**
> 分域报告：`01-parts.md` `02-products.md` `03-baselines-effectivity.md` `04-documents.md` `05-workspace.md` `06-workflow-change-tasks.md` `07-query-importer.md` `08-crosscutting.md`（每条 CRITICAL/HIGH 均含 `复核：` 裁决行）
> 修复计划：`FIX-PLAN.md`

---

## 一、问题总计（经独立复核修订后）

| 域 | CRITICAL | HIGH | MED | LOW | 说明 |
|----|:---:|:---:|:---:|:---:|----|
| 1 Parts | 0 | 1 | 7 | 3 | P1-01 降 MED、P1-03/05 降 MED |
| 2 Products | 1 | 5 | 4 | 3 | P2-01 CRIT→HIGH |
| 3 Baselines/Effectivity | 0 | 3 | 3 | 4 | 3 HIGH 全 CONFIRMED |
| 4 Documents | 1 | 7 | 6 | 2 | P4-03 降 MED |
| 5 Workspace/用户/权限 | 2 | 5 | 4 | 3 | 全 CONFIRMED |
| 6 Workflow/Change/Tasks | 2 | 6 | 4 | 2 | P6-01/04 CRIT→HIGH、P6-05 证伪撤销 |
| 7 Query/Importer | 0 | 1 | 7 | 4 | P7-02 证伪降 LOW、P7-03 降 MED |
| 8 横切/其他 | 0 | 1 | 5 | 3 | P8-01 降 MED、P8-03 降 LOW |
| **合计** | **6** | **29** | **40** | **24** | 初判 10C/34H → 复核后 6C/29H |

> 初判 → 复核变化：CRITICAL 10→**6**（4 降级）；HIGH 34→**29**；证伪 2 项（P6-05、P7-02）。

---

## 二、6 个确认的真 CRITICAL（复核 CONFIRMED，均可直接修复）

| # | 编号 | 问题 | 文件 | 症状 | 修复 |
|---|------|------|------|------|------|
| C1 | P2-02 | search_ci_numbers 参数错序 | `routers/products.py:97` | `_ci_to_dict(db,c)`（签名 `(ci,db)`）→ Session 上 AttributeError，所有 `/products/numbers?q=` 搜索必 500 | 改 `_ci_to_dict(c,db)`（一行）|
| C2 | P4-01 | 文档 attachedFiles 永空 | `routers/document.py:131` | _doc_to_dict（GET /documents/{key} 唯一序列化路径，32 处调用）attachedFiles 硬编码 `[]`，前端看不到附件 | 查 documentiteration_binres+binaryresource 填充 |
| C3 | P5-01 | delete_workspace 漏删 folder | `services/workspace_deletion.py` | 全文无 DELETE FROM folder；GD50 有 2 行 folder 永久残留孤儿（第一轮 W-1 修复遗漏抽取函数本身）| 补 UPDATE folder parentfolder=NULL + DELETE folder |
| C4 | P5-02 | workspaces.py NameError | `routers/workspaces.py:148,241,422` | 用 `Path`/`settings`/`indexer_manager` 但未 import → disk-usage/reindex/create 首次调用即崩溃 | 补 import |
| C5 | P6-02 | change 文档 affected 硬编码 iteration=1 | `routers/change_common.py:226-230` | _set_affected_documents 写死 iteration=1（_set_affected_parts 正确查 MAX）；DB 确认 FK→documentiteration；iteration>1 时 FK 500 | 查 MAX(iteration) 或从 body 取 |
| C6 | P6-03 | WorkflowActivityDTO 状态字段全 0 | `routers/workflow.py:44-50` | complete/stopped/inProgress/toDo/relaunchStep 未填充（Pydantic 默认 0/False），前端无法展示工作流活动进度 | 按 task status 统计填充 |

> C1/C2/C5 涉 500，仅 GD50 有数据环境暴露（空库测不到，清单#18）；修复后须 GD50 复测 + pytest 282 基线。

---

## 三、29 个 HIGH（复核后）

### 权限 / 安全（最紧要）
- **P1-04** get_latest_revision 无 ACL 检查 → 信息泄露（Java canAccess→403）
- **P4-02** release 缺 write access；**P4-04** move_document 缺权限；**P4-05** delete_folder 缺 home/root/他人home 保护（可删根级联损毁）；**P4-06** move_folder 缺 home/root/跨工作区保护；**P4-08** update_doc_acl 缺 admin/author 检查 + 缺空 ACL removeACL 分支
- **P4-07** delete_template 直接删 acl 未先删 entries → FK 500
- **P5-07** admin.py get_platform_options/get_index 缺认证/admin 检查

### DTO / 返回结构对齐
- **P2-03** PathData getPathData partLinksList/partAttributes/partAttributeTemplates 全空
- **P2-04** get_product_instance iteration 缺 11 字段
- **P3-01** baseline substituteLinks/optionalUsageLinks 类型错（对象数组 vs 路径字符串）
- **P3-02** EffectivityDTO 缺 configurationItemKey 嵌套对象
- **P4-09** inverse_path_link 缺 partLinksList/serialNumber
- **P5-03** remove_from_group 返回错误 group DTO（非崩溃）
- **P5-04** setUserAccess 返回 `{"status":"ok"}` 而非 UserDTO+缺 membership null→400
- **P5-05** setGroupAccess 返回 `{"status":"ok"}`（`user_groups.py:141`）
- **P5-06** my_memberships 返回列表（Java 单对象）+ 多 permission 字段
- **P6-06** workflow_models updateACL 返回 200（Java 204）
- **P6-07** milestones updateACL 返回 200（Java 204）
- **P6-09** get_instance currentStep 硬编码 0

### 功能行为 / 缺失
- **P2-05** hasPathData CI ID 含连字符计算错（仅非 visitor 路径，正常 3D 不受影响）
- **P2-06** pi-{serial} configSpec 降级为 latest（绕过实例基线解析）
- **P3-03** put_effectivity 不按类型校验（可清空下限字段）
- **P8-02** organizations move_member 只上移（忽略 direction）
- **P7-01** import_into_path_data stub（Java doPathDataImport 有完整实现）
- **P6-08** instantiate_workflow 缺审批通知邮件

### 由 CRITICAL 降级为 HIGH（数据累积后触发）
- **P2-01** delete_instance 未清 7 张子表 → FK 500（GD50 子表当前空）
- **P6-01** process_task 缺通知副作用/checkedOut 防护（核心状态机已对齐）
- **P6-04** relaunchStep 未写 activitymodel_relaunch（relaunch 仍可用）

---

## 四、复核降级 / 证伪明细

| 编号 | 原级 | 复核后 | 原因 |
|------|:---:|:---:|------|
| P1-01 | CRIT | MED | set_tags 会 500 属实，但前端只用 POST/DELETE，不调 PUT set_tags |
| P2-01 | CRIT | HIGH | FK 真实，但 GD50 子表当前空，潜在缺陷 |
| P6-01 | CRIT | HIGH | 核心状态机已对齐；缺通知/防护。原报告"Java releaseDocument"不准确 |
| P6-04 | CRIT | HIGH | relaunch 仍可用（从当前 step），非完全缺失 |
| P1-03 | HIGH | MED | 返回类型不匹配属实，但前端未调用该端点 |
| P1-05 | HIGH | MED | 缺 SubResource DELETE 文件路径，仅影响 checkin 取消已传文件（低频）|
| P4-03 | HIGH | MED | Python 更严（仅本人 undo），Java 允许 admin——功能缺陷非安全漏洞 |
| P7-03 | HIGH | MED | Java 非"全成全败"（ApplicationException 被 catch 后照样提交）；附带独立 bug errors:[] 丢弃 |
| P8-01 | HIGH | MED | Java @ManyToMany 也不删 marker，当前结果反而与 Java 一致，属死代码 |
| P8-03 | HIGH | LOW | 纯响应形态差异（200+DTO vs 204），功能正确 |
| **P6-05** | HIGH | **REFUTED** | Java WorkflowModel 也无 reference，Dozer 后同为 null，无偏差（撤销）|
| **P7-02** | HIGH | **REFUTED→LOW** | Java BomImporter 无实现，doBomImport 死代码 → Python stub 是对齐行为 |

---

## 五、澄清的 Phase-0 / 历史误报

| 项 | 结论 |
|----|------|
| ProductBaselineCreationDTO author 422（工具 CRIT）| 假报：Java 无 author 字段，Python 端点用 body:dict 无 extra=forbid |
| PathDataIterationCreationDTO partLinksList 422（工具 CRIT）| 假报：工具误映射到响应 DTO；端点用 body:dict |
| DELETE /roles STUB（audit_write_stubs）| 假报：delete_role 实际 db.delete+commit，脚本删后与初始态对比误判 |
| PUT /workflow-models update STUB | 假报：update_model 实际改 finalLifecycleState + 重建 ActivityModel + commit |
| dtype 写入设计分歧（loose-ends）| 不成立：_sync_instance_attributes 实际已写 dtype；importer.py:40-43 docstring 过时 |
| validate_sql_columns `id` NOT-NULL 缺失（15 处）| 假报：均自增序列 id（RETURNING）|
| `UPDATE SET 表不存在`（users/user_groups/workspace_memberships）| 假报：工具把 `ON CONFLICT DO UPDATE SET` 误判为表名 |
| check_hardcoded_exceptions | 干净 |

---

## 六、附带发现（复核新增）

- **P7-03 独立 bug**：`importer.py:217` import_into_parts 返回硬编码 `errors:[]`，checkout 失败错误被丢弃，调用方不可见。
- **行号更正**：P5-05 实际在 `user_groups.py:141`（原误标 workspace_memberships.py:141）。
- **原报告不准确的 Java 断言**（修复时以复核为准）：P6-01（Java 无 releaseDocument）、P7-03（Java 非全成全败）。

> 修复路线见 `FIX-PLAN.md`：4 个修复批次（批 1=6 CRITICAL；批 2=权限安全 HIGH；批 3=workflow/change/baseline HIGH；批 4=products/query HIGH），MED/LOW 收尾在批 5。
