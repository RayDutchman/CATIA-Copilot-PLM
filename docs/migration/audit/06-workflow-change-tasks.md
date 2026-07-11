# Workflow/Change/Tasks 域审计报告

> 审计员：explore subagent ｜ 日期：2026-07-11 ｜ 波次：2
> 范围：workflow.py / workflow_models.py / tasks.py / milestones.py / change_common.py / change_issues.py / change_orders.py / change_requests.py / workflow_manager.py / task_manager.py / change_manager.py
> 方法：纯代码对照（GD50 环境几乎无数据）

## 问题 WF-1
- 严重级：CRITICAL
- 类别：要点#17（端点语义偏差）
- 位置：`app/routers/workflow.py:60-65` + `app/services/workflow_manager.py:221-239`
- Java 对照：`WorkflowResource.java:105-123` → `WorkflowManagerBean.java:387-419`
- 证据：Java getWorkflowAbortedWorkflowList 按 workflowId 查持有者（文档/零件/ws_workflow），返回持有者的 getAbortedWorkflows() 列表(List<WorkflowDTO>)。Python 直接查 `workflow WHERE id=:id AND aborteddate IS NOT NULL` 返回单个，格式也不同。
- 结论与建议：改为查持有者→再查其 aborted workflow 列表。

## 问题 WF-2
- 严重级：HIGH
- 类别：要点#17 + #2
- 位置：`app/routers/workflow.py:68-74`（list_wwf）
- Java 对照：`WorkflowManagerBean.java:465-468`
- 证据：Python 查 `workflow.*` 但 r[0] 赋给 WorkspaceWorkflowMinimalDTO.id——workflow.id 是整数，workspace_workflow.id 是 UUID，类型不匹配。
- 结论与建议：返回 workspace_workflow.* 而非 workflow.*。

## 问题 WF-3
- 严重级：HIGH
- 类别：要点#5 + #1
- 位置：`app/services/workflow_manager.py:275-279`（instantiate_workflow）
- 证据：用 `SELECT currval('workflow_id_seq')` 取 ID，同一事务多 INSERT 时不可靠。
- 结论与建议：改 `INSERT ... RETURNING id`。

## 问题 WF-4
- 严重级：HIGH
- 类别：要点#14 + #7
- 位置：`app/services/workflow_manager.py:260-364`
- Java 对照：`WorkflowManagerBean.java:312-361`
- 证据：Java 末尾 notifier.sendApproval 发审批通知邮件，Python 完全未实现通知发送。
- 结论与建议：补 notifier 调用。

## 问题 TASK-1
- 严重级：CRITICAL
- 类别：要点#14（状态一致性）
- 位置：`app/services/task_manager.py:171-271`（process_task）
- Java 对照：`TaskResource.java:252-307` + Document/PartWorkflowManagerBean
- 证据：Java 按 holderType 分发到不同 Manager，除更新 task 状态外还更新文档/零件 lifeCycleState + 发通知 + 检查 relaunch。Python 统一处理只更新 task + _advance_activity，**不更新持有者生命周期状态**。
- 结论与建议：补工作流完成时的 lifecycle state 更新。

## 问题 CH-1
- 严重级：CRITICAL
- 类别：要点#6（权限/ACL 展示）
- 位置：`app/routers/change_common.py:35-41`（_get_acl_dict）
- 证据：`userGroupEntriesMap: {}` 硬编码空。Java Dozer 自动映射 groupEntries。
- 结论与建议：填充 userGroupEntriesMap（group_id→permission）。

## 问题 CH-2 ~ CH-5（HIGH）
- **CH-2**(要点#2)：change_manager.py:141-163 update_item 允许更新任意 key（含不可变 name），Java updateChangeIssue 只更 description/priority/category。加白名单。
- **CH-3**(要点#17)：change_orders.py:48-58 新增 Java 无的 `/orders/link` 端点。确认是否误加。
- **CH-4**(要点#5)：change_common.py:179-183 _set_affected_parts 硬编码 iteration=1，Java 取实际迭代号。
- **CH-5**(要点#6)：_set_affected_parts/_set_affected_documents 无 ACL 级 checkChangeItemWriteAccess。

## 问题 TASK-2 ~ TASK-3（HIGH）
- **TASK-2**(要点#21)：tasks.py:204-223 process_task 返回 holder(200)，Java 返回 204。
- **TASK-3**(要点#6+#7)：tasks.py:150-180 _verify_downloaded 支持文档+零件+ws-workflow 且用 checkoutuser 匹配，Java checkTask 仅文档+DOWNLOAD 事件日志。行为不一致。

## 问题（MEDIUM）
- **WF-5**(要点#6)：workflow_manager.py:45-51 _check_write_access 依赖 acl_factory 对 None ACL 的处理，需核实是否检查 workspace 写权限。
- **WF-6**(要点#17)：workflow.py:54 get_instance 硬编码 `currentStep: 0`。
- **WF-7**(要点#17)：workflow_models.py update_model_acl 不处理空 ACL 删除，返回 200 应 204。
- **TASK-4**(要点#2)：tasks.py:130-147 get_task 缺 assignedUsers/assignedGroups/targetIteration。
- **TASK-5**(要点#3)：tasks.py:230-254 task_documents 缺 iterationSubscription/stateSubscription。
- **CH-6**(要点#14)：change_common.py _set_affected_parts/documents 各自独立 commit，半成品风险。
- **CH-7**(要点#2)：milestones.py:44-55 dueDate 非标准格式化。
- **CH-8**(要点#17)：change_issues/orders/requests remove_tag 返回 200，Java 返回 204。

## 问题（LOW）
- **WF-8**(要点#2)：workflow_models.py reference/id 字段对照需确认。
- **WF-9**(要点#1)：tasks.py _task_row_to_dict 依赖裸 SQL 列位置索引 row[13] 等，脆弱。

## 小结
| 严重级 | 数量 |
|--------|------|
| CRITICAL | 3 | WF-1、TASK-1、CH-1 |
| HIGH | 8 | WF-2、WF-3、WF-4、TASK-2、TASK-3、CH-2、CH-3、CH-4、CH-5（注：实为9项，含CH-5） |
| MEDIUM | 8 | WF-5、WF-6、WF-7、TASK-4、TASK-5、CH-6、CH-7、CH-8 |
| LOW | 2 | WF-8、WF-9 |

整体：CRUD 骨架已实现约 60-70% 端点，但 3 个 CRITICAL 语义错误（WF-1 aborted 端点逻辑全错、TASK-1 缺生命周期更新、CH-1 groupEntriesMap 空）。通知发送完全缺失，迭代号硬编码。建议优先修 CRITICAL + HIGH。
