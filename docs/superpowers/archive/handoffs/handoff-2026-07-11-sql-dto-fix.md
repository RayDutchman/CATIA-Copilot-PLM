# Handoff 2026-07-11 — SQL 列名 + DTO 字段修复

> 上一会话修复了 6 个运行时 bug（403权限/500表名/500列名/422字段缺失/dtype缺失）。
> 新增了两套自动化验证脚本，扫描发现了 **31 处 SQL 列名错误** + **3 个 DTO 缺失字段**。
>
> **目标**: 修复脚本 1 报告的全部 31 处 SQL 列名错误，修复脚本 2 报告的 3 个 CRITICAL DTO 缺失。

---

## 前置操作（启动时执行）

1. `docker cp` + `docker restart back-py` 部署方式不变
2. 验证脚本存放位置: `scripts/validate_sql_columns.py` + `scripts/validate_dto_fields.py`
3. 每次修完一批→跑两脚本→确认问题减少→继续下一批

---

## 任务 1: 修复 31 处 SQL 列名/表名错误

**运行**: `cd docdoku-plm-server-py && python3 scripts/validate_sql_columns.py`

### A 类: 表名不存在（绝对 500）— 6 处

| 文件:行号 | 错误表名 | 实际表名 | 说明 |
|-----------|---------|---------|------|
| `routers/product_instances.py:81` | `productinstanceiteration_documentlink` | 不存在 | 查 DB 确认正确表名 |
| `services/notification_manager.py:44` | `tagsubscription` | `tagusersubscription` | 用户标签订阅 |
| `services/product_manager.py:289` | `workflow_usergroup` | 不存在 | workflow 用户组 |
| `services/product_manager.py:294` | `workflow_usergroup` | 同上 | 同上 |
| `services/webhook_manager.py:61` | `simplewebhookapp` | 不存在 | webhook |
| `services/webhook_manager.py:73` | `snswebhookapp` | 不存在 | webhook |

### B 类: 列名错误/别名问题 — 25 处

| 文件:行号 | 错误列 | 实际列 |
|-----------|--------|--------|
| `routers/attributes.py:41` | `ia.attributetype` | 不存在（instanceattribute 表无此列） |
| `routers/attributes.py:41` | `ia.lov_name` | 不存在 |
| `routers/attributes.py:67` | `pdi.workspace_id` | pathdataiteration 无此列 |
| `routers/attributes.py:67` | `pdi.configurationitem_id` | pathdataiteration 无此列 |
| `routers/attributes.py:67` | `pdi.serialnumber` | pathdataiteration 无此列 |
| `routers/document.py:433-481` | 多个列名错误 | 见脚本输出 |
| `routers/tasks.py:161` | `checkout_user_login` | `checkoutuser_login` |
| `routers/tasks.py:171` | `checkout_user_login` | `checkoutuser_login` |
| `services/cascade_action_manager.py:30` | `creation_date` | `creationdate` |
| `services/file_export/instance_body_writer_tools.py:165` | `component_partversion` | 不存在 |
| `services/organization_manager.py:13` | `organization_name` | 不存在 |
| `services/products/part_workflow_manager.py:33` | `abortedworkflows` | 不存在 |

**修复方法**: 对每个错误，先用 `postgres_query` 查 `information_schema.columns` 确认实际列名，再修改 SQL。

**验证**: 每修复一批跑 `python3 scripts/validate_sql_columns.py`，确认错误数递减。

---

## 任务 2: 修复 3 个 CRITICAL DTO 缺失字段

**运行**: `cd docdoku-plm-server-py && python3 scripts/validate_dto_fields.py`

3 个 Pydantic schema 带有 `extra='forbid'` 但缺少 Java DTO 所需的字段。客户端发送这些字段时会被 **422 拒绝**。

| Python Schema | 缺失字段 | Java DTO | 影响 |
|---------------|---------|----------|------|
| `UserDTO` (app/schemas/part/user.py) | `membership` | UserDTO 有 `WorkspaceMembership membership` | 响应中无用户角色信息 |
| `WorkspaceWorkflowCreationDTO` | `workflow` | 有 `WorkflowDTO workflow` | 创建工作流 422 |
| `ConversionResultDTO` (app/schemas/part/conversion_result.py) | `partIterationKey` | 有 `PartIterationKey partIterationKey` | 转换回调 422 |

**此外**，有 28 个 WARNING 级别的不一致（Python schema 字段比 Java DTO 多），大多是 **响应 DTO 包含了 Java 请求 DTO 的字段**，这是正常的——Python 的 schema 同时用于请求和响应，Java 是分开的。暂不处理。

---

## 工具使用

```
# 每次修复后验证
python3 scripts/validate_sql_columns.py

# DTO 字段验证
python3 scripts/validate_dto_fields.py

# 查询实际列名
# 用 postgres_query 工具: SELECT column_name FROM information_schema.columns
# WHERE table_name='xxx' ORDER BY ordinal_position
```

---

## 注意事项

- 对齐 Payara 铁律不变
- docker cp + restart 部署
- 修复完一批后更新 `docs/CHANGELOG.md` 的当天条目
- 完成后勾选 `docs/migration/loose-ends.md` 相关条目
