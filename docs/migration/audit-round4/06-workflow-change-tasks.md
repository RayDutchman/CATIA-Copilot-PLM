# 域6 Workflow/Change/Tasks 工作流/变更/任务 审计报告（第4轮）

> 生成日期：2026-07-12 ｜ 范围：`docdoku-plm-server-py` 工作流/变更/任务迁移代码 vs Java/Payara
> 方法：explore subagent 逐端点对照 + information_schema 核实 + GD50 验证
> 基准 workspace = GD50 ｜ **只读审计，未做任何修复**

## 结论
**0 CRITICAL / 2 HIGH / 1 MED / 2 LOW**。第2轮 2 CRITICAL（P6-02/03）+ 多个 HIGH 在第3轮重构中修复。本轮新发现 1 HIGH（holderType 单复数不一致，前端路由错）。P6-08 审批通知邮件缺失属**已知计划外项**（邮件族未迁移，loose-ends 第八节）。

---

## HIGH

### P6-17 holderType 单复数与 Java 不一致 → 前端任务路由错
- 严重级：HIGH
- 类别：清单#2（DTO字段对齐）、#8（数据格式）
- 文件：`app/services/task_manager.py:46`（"part"）、`:52`（"workspace-workflow"）、`:566,582`（_relaunch_workflow 同） | Java对照：`TaskManagerBean.java:142/151/160`
- 证据：Java 严格用复数：line 142 `"documents"`（Python `"documents"` ✓）、**line 151 `"parts"`（Python `"part"` ✗）、line 160 `"workspace-workflows"`（Python `"workspace-workflow"` ✗）**。前端 JS 依赖这些字符串决定 UI 组件类型和导航链接，不匹配 → 零件任务/工作流审批被错误路由。影响 get_assigned_tasks / get_task_dto / process_task 返回值。
- 建议修复：`_resolve_holder` 与 `_relaunch_workflow` 统一改 `"parts"`/`"workspace-workflows"`（约 12 处引用）。
- 与前两轮关系：新发现。

### P6-01 process_task 缺审批后副作用（release/通知）
- 严重级：HIGH（第2轮由 CRITICAL 降级，核心状态机已对齐）
- 类别：清单#8（状态机逻辑）、#3（通知副作用 TODO）
- 文件：`app/services/task_manager.py:401-403,420-426`（TODO 通知/release） | Java对照：`TaskResource.java:276-304` 按 holderType 分派，有 sendApproval/releaseDocument 等副作用
- 证据：checkedOut 防护已实现（L380-391）✓；任务审批/状态机/advance_activity/relaunch 已对齐 ✓；但审批后文档 release + 索引更新 + 状态通知邮件仍缺（明确 TODO）。
- 建议修复：实现文档审批后 release + 邮件通知（邮件属已排期 loose-ends 第八节）。
- 与前两轮关系：仍存在（部分属已知邮件族排期）。

---

## MED

### P6-18 assignedUsers 从未填充
- 严重级：MED
- 类别：清单#2（DTO字段对齐）
- 文件：`app/services/task_manager.py:145-167`(get_assigned_tasks)、`183-205`(get_task_dto) | Java对照：`TaskDTO.java:60-61` `List<UserDTO> assignedUsers`
- 证据：TaskWrapperDTO/TaskDTO 的 `assignedUsers: List[UserDTO] = []` 有默认值不报错，但返回 dict 从不含 `assignedUsers` key → 始终空。assignedGroups 已在 L160-166 填充。
- 建议修复：查 `task_user` 表填充 assignedUsers。
- 与前两轮关系：前轮 P6-11 部分修（groups 已修，users 仍缺）。

---

## LOW
- **P6-08** instantiate_workflow 缺审批通知邮件（`workflow_manager.py:439-451` 明确 TODO）——**已知计划外项**，邮件族全量迁移已排期（loose-ends 第八节），此处仅记录不重复定级为 HIGH。
- **P6-14** `_task_row_to_dict` 用 `row[13]`/`row[9]` 索引访问，schema 变更静默读错。前轮已知。
- **P6-15** `_NAME_CACHE` 模块级字典无 TTL/上限。前轮已知。

---

## 第2轮问题复核（已闭环，本轮确认）
| 编号 | 原级 | 新代码位置 | 结论 |
|------|------|-----------|------|
| P6-02 | CRITICAL | `change_manager.py:515-522` set_affected_documents 查 MAX(iteration) | ✅ 已修复 |
| P6-03 | CRITICAL | `workflow_manager.py:497-553` enrich_activity_dicts 填 complete/stopped/inProgress/toDo/relaunchStep | ✅ 已修复 |
| P6-04 | HIGH | `workflow_manager.py:117-137/162-195` create/update_model 写 activitymodel_relaunch | ✅ |
| P6-06/07 | HIGH | workflow_models/milestones updateACL 返回 204 | ✅ |
| P6-09 | HIGH | enrich_activity_dicts currentStep 逐活动累加至首个未完成 | ✅ |
| P6-10/12/13 | MED | list_models 补 access 检查 / STATUS_MAP 含 NOT_TO_BE_DONE / change set_tags 传 user_login+is_admin | ✅ |
| P6-05 | — | Java WorkflowModel 也无 reference | 前轮已证伪 |

## 已核对一致的要点
| 要点# | 结论 |
|-------|------|
| #1 裸SQL | workflow/activity/task/task_user/task_usergroup/workspace_workflow/activitymodel/taskmodel/changeissue/changerequest/changeorder/milestone + affected/acl 表核实正确；`\d activitymodel_relaunch`/`\d changeissue_affected_document`(FK→documentiteration) 确认 |
| #3 硬编码桩 | 无（enrich_activity_dicts 非桩） |
| #4 级联删除 | delete_workspace_workflow/delete_model/delete_item 按 FK 顺序清理 |
| #6 权限 | 路由级/service级一致 |
| #7 异常一致性 | service 层全领域异常，无 HTTPException |
| #16 SQL注入 | 表名/列名硬编码 map，值走绑定参数 |
| #17 端点覆盖 | Issues/Orders/Requests/Milestones/Workflow CRUD+tags+affected+ACL+实例化+aborted+tasks 全覆盖 |
| #22 GD50 | assigned tasks/workflow-models/issues/milestones curl 冒烟正常 |
