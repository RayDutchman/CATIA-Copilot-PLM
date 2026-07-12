# [Workflow/Change/Tasks] 审计报告（域6）

> 第二轮迁移代码审计 ｜ 只读代码对比 ｜ 基准 workspace = GD50

**总体结论**：端点全覆盖，核心 CRUD 与任务审批状态机基本正确。2 CRITICAL / 6 HIGH / 4 MED / 2 LOW（经独立复核修订；P6-05 证伪撤销）。Phase-0 的 PUT /workflow-models update STUB 经核实为**假报**（实际写库）。

---

## 问题 P6-01
- 严重级：HIGH（原 CRITICAL，复核调整）
- 复核：SEVERITY-ADJUST→HIGH。核心状态机（advance/lifecycle/relaunch）已对齐；缺的是通知类副作用（sendApproval 邮件/state notification/GCM）+ checkedOut 防护。原报告"Java 有 releaseDocument"不准确——Java 无显式 release，靠 JPA 内存状态机，Python 已对齐。
- 类别：清单#8（状态机逻辑对齐）
- 文件：`app/services/task_manager.py:215-270`（process_task）
- Java对照：`TaskResource.java:276-304`
- 证据：Java processTask 按 holderType 路由到 document/part/workflow 三个 Manager，各有副作用（如文档审批后 releaseDocument/触发索引）；Python 统一只做 UPDATE task status + _advance_activity，跳过 holder 特定逻辑。
- 建议修复：审查 Java DocumentWorkflowManager.approveTaskOnDocument / PartWorkflowManager.approveTaskOnPart 副作用并补全。

## 问题 P6-02
- 严重级：CRITICAL
- 复核：CONFIRMED。_set_affected_documents 硬编码 iteration=1（_set_affected_parts 正确取 MAX）；DB 确认 changeissue/order/req_affected_document 均 FK→documentiteration；文档 iteration>1 时 FK 500。维持 CRITICAL。
- 类别：清单#5（INSERT 列完整性）
- 文件：`app/routers/change_common.py:226-230`（_set_affected_documents）
- Java对照：`ChangeIssuesResource.java:389-397`（用 dto.getIteration()）
- 证据：硬编码 `iteration=1`；_set_affected_parts 正确查 MAX(iteration)。文档 iteration>1 时 FK 违约 → 500。
- 建议修复：文档也查 MAX(iteration) 或从 body 取。

## 问题 P6-03
- 严重级：CRITICAL
- 复核：CONFIRMED。activity dict 缺 complete/stopped/inProgress/toDo/relaunchStep（Pydantic 默认 0/False）；Java ActivityDozerConverter 显式填充。前端无法展示工作流活动进度。维持 CRITICAL。
- 类别：清单#2（DTO 字段对齐）
- 文件：`app/routers/workflow.py:44-50`（get_instance / get_workspace_workflow）
- Java对照：`WorkflowResource.java:84-91`（Dozer 自动算 complete/stopped/inProgress/toDo）
- 证据：WorkflowActivityDTO 的 complete/stopped/inProgress/toDo/relaunchStep 未填充，全为默认 0/False/None，前端无法展示活动进度。
- 建议修复：按 task status 统计计算这些字段。

## 问题 P6-04
- 严重级：HIGH（原 CRITICAL，复核调整）
- 复核：SEVERITY-ADJUST→HIGH。relaunchStep 确不写 activitymodel_relaunch，但 Python relaunch 仍可用（从当前 step 重置）；Java 无配置时根本不 relaunch，功能差异非完全缺失。
- 类别：清单#17（端点覆盖缺口/功能缺失）
- 文件：create_model/update_model（workflow_models.py）忽略 relaunchStep
- Java对照：`WorkflowModelResource.java:208-224`（extractActivityModelFromDTO 写 activitymodel_relaunch）
- 证据：Python 完全忽略 ActivityModelDTO.relaunchStep，activitymodel_relaunch 表永不写入 → 拒绝工作流无法回到指定步骤（relaunch 失效）。_relaunch_workflow 逻辑存在但配置数据从未存储。
- 建议修复：create_model/update_model 处理 relaunchStep 写 activitymodel_relaunch。

## 问题 P6-05
- 严重级：REFUTED 证伪（原 HIGH）
- 复核：REFUTED。Java WorkflowModel 无 reference 字段/getter，Dozer 映射后 Java 响应同为 null，与 Python 一致，无偏差。撤销此问题。
- 类别：清单#2
- 文件：`app/routers/workflow_models.py:70-85`（_model_to_dict）
- Java对照：`WorkflowModelDTO.java:131-132`（reference 默认=id）
- 证据：reference 字段从未设置，响应永远 None（Java 默认等于 id）。
- 建议修复：result 加 `"reference": m.id`。

## 问题 P6-06
- 严重级：HIGH
- 复核：CONFIRMED。workflow_models updateACL 返回 200+DTO（Java 204）。
- 类别：清单#15（状态码）
- 文件：`app/routers/workflow_models.py:133-143`（updateACL）
- Java对照：`WorkflowModelResource.java:171-183`（204）
- 证据：Java 返回 204 无 body，Python 返回 200+完整 DTO。
- 建议修复：返回 Response(status_code=204)。

## 问题 P6-07
- 严重级：HIGH
- 复核：CONFIRMED。milestones updateACL 返回 200+body（Java 204）。
- 类别：清单#15（状态码）
- 文件：`app/routers/milestones.py:131-143`（updateACL）
- Java对照：`MilestonesResource.java:251-264`（204）
- 证据：Java 返回 204，Python 返回 200+`{"aclId":...}`。
- 建议修复：返回 204。

## 问题 P6-08
- 严重级：HIGH
- 复核：CONFIRMED。instantiate_workflow 缺审批通知邮件（明确 TODO；Java notifier.sendApproval）。
- 类别：清单#5 / #3（TODO 桩）
- 文件：`app/services/workflow_manager.py:406`（instantiate_workflow）
- Java对照：`WorkflowManagerBean.java` L359（notifier.sendApproval）
- 证据：明确 TODO 缺审批通知，Java 实例化后向每个 task worker 发邮件；Python 未实现，用户收不到审批通知。
- 建议修复：实现 sendApproval 遍历 running tasks worker 发邮件。

## 问题 P6-09
- 严重级：HIGH
- 复核：CONFIRMED。get_instance currentStep 硬编码 0（Java getCurrentStep 遍历 activities 计算）。
- 类别：清单#2
- 文件：`app/routers/workflow.py:51-57`（get_instance）
- 证据：currentStep 永远硬编码 0，Java 由 getter 计算，前端依赖此定位审批步骤。
- 建议修复：计算真正 currentStep。

## 问题 P6-10
- 严重级：MED
- 类别：清单#11 / #6
- 文件：`app/routers/workflow_models.py:88-93`（list_models）
- Java对照：`WorkflowModelResource.java:82-94`（@RolesAllowed + 读权限）
- 证据：list_models 路由不调 _check_workspace_access，非成员仍可列出无 ACL 的 model。
- 建议修复：加 _check_workspace_access。

## 问题 P6-11
- 严重级：MED
- 类别：清单#2
- 文件：`app/schemas/workflow/__init__.py:68`（TaskWrapperDTO.assignedGroups）
- Java对照：`TaskDTO.java:60-61`（List<UserGroupDTO>）
- 证据：assignedGroups 从未填充，响应永远空列表。
- 建议修复：从 task_usergroup 查填充。

## 问题 P6-12
- 严重级：MED
- 类别：清单#2 / #8
- 文件：`app/schemas/workflow/task.py:14`
- Java对照：`TaskDTO.java:66`（TaskStatus 枚举）
- 证据：STATUS_MAP 只映射 {0,1,2,3}，缺 `4: NOT_TO_BE_DONE`，DB status=4 时返回 None。
- 建议修复：加 4:NOT_TO_BE_DONE。

## 问题 P6-13
- 严重级：MED
- 类别：清单#6 / #15
- 文件：`app/services/change_manager.py:281-298`（set_tags）
- Java对照：`ChangeIssuesResource.java:227-246`
- 证据：set_issue_tags/set_order_tags/set_request_tags 路由调 set_tags 未传 user_login → check_write_access(acl_id,None,False) 权限检查可能被绕过（对比 update_item/delete_item 正确传参）。
- 建议修复：路由传 user_login=current_user.login + is_admin。

## 问题 P6-14 / P6-15 / P6-16
- 严重级：LOW
- P6-14：workflow_manager.py:439-443 `SELECT *`+索引取值依赖列序，schema 变更静默读错 → 建议命名列访问。
- P6-15：change_common.py:11 `_NAME_CACHE` 模块级无限增长缓存，无 TTL → 建议 lru_cache。
- P6-16：tasks.py:223 process_task 返回 204 无 body，已核对一致，无需修复。

---

## 已核对一致的要点
- PUT /workflow-models update **非 STUB**：update_model 实际改 finalLifecycleState + 重建 ActivityModel + commit。Phase-0 假阳性（空 body 无变化）。
- #1 裸 SQL：workflow/activity/task/task_user/task_usergroup/workspace_workflow/activitymodel/taskmodel/changeissue/changerequest/changeorder/milestone 及各 affected/关联表列名全部核实正确。
- INSERT workflow 缺 id 为自增 RETURNING，Phase-0 误报。
- #6 权限：_check_workspace_access/check_write_access/_is_admin 逻辑一致。
- #8 状态机：APPROVE→2/REJECT→3、_advance_activity tasksToComplete、Sequential/Parallel、_relaunch_workflow clone+abort 主流程对齐。
- #17：Issues/Orders/Requests/Milestone CRUD+tags+affected+ACL 全覆盖。
- #4 级联：delete_workspace_workflow 与 delete_item 按 FK 顺序清理。
- #16 SQL 注入：表名/列名硬编码 map，值走绑定参数。
