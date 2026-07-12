# 域5 Workspace/用户/权限/Admin 审计报告（第4轮）

> 生成日期：2026-07-12 ｜ 范围：`docdoku-plm-server-py` 工作区/用户/权限/Admin 迁移代码 vs Java/Payara
> 方法：explore subagent 逐端点对照 + information_schema FK 核实 + GD50 验证；主 agent 已核实 P5-19
> 基准 workspace = GD50 ｜ **只读审计，未做任何修复**

## 结论
**0 CRITICAL / 3 HIGH / 3 MED / 2 LOW**。第2轮 2 CRITICAL（P5-01/02）已闭环。本轮发现权限检查系统性缺口：7 个用户组/成员端点缺 admin 校验、8 个 admin stats 端点缺 admin 校验（第2轮 P5-07 部分回归），及 setUserAccess UPSERT→500 语义偏离。

---

## HIGH

### P5-19 用户组/成员 7 个写端点缺 admin 权限校验（权限绕过）
- 严重级：HIGH
- 类别：清单#6（权限检查逐行对比）
- 文件：`app/routers/user_groups.py:33,43,58,72,84`；`app/routers/workspace_memberships.py:77,92` | Java对照：`UserManagerBean.java` 所有写操作首行 `checkAdmin(pWorkspaceId)`（createUserGroup:155、removeUserFromGroup:87、grantUserAccess:251 等）
- 证据（**主 agent 已核实**）：以下端点 router 无 `_check_workspace_admin`、service 也无 admin 检查：
  | 端点 | 文件:行号 |
  |------|----------|
  | POST /groups (create_group) | user_groups.py:33 |
  | DELETE /groups/{id} (delete_group) | user_groups.py:43 |
  | PUT /enable-group | user_groups.py:58 |
  | PUT /disable-group | user_groups.py:72 |
  | PUT /group-access | user_groups.py:84 |
  | PUT /add-user | workspace_memberships.py:77 |
  | PUT /remove-from-workspace | workspace_memberships.py:92 |
  对比 enable-user(136)/disable-user(148)/set_user_access(168)/set_admin(119) 已正确加 `_check_workspace_admin`。核实 `create_group`/`delete_group` 的 service（`user_manager.py`）内部也无 admin 检查。
- 建议修复：7 个端点统一补 `_check_workspace_admin(db, ws, current_user)`。
- 与前两轮关系：新发现/回归（第3轮 Batch1 统一 Depends 时遗漏这批端点）。

### P5-07-REG admin stats + index 8 个端点缺 admin 校验（部分回归）
- 严重级：HIGH
- 类别：清单#6
- 文件：`app/routers/admin.py:153,160,167,174,181,190`；`app/routers/accounts.py:57,64` | Java对照：`AdminResource.java:62-63` **类级** `@RolesAllowed(ADMIN_ROLE_ID)` 覆盖全部方法
- 证据：第2轮 P5-07 指出 get_platform_options/get_index 缺认证——**这两个已修（403 确认）**。但 disk-usage-stats/users-stats/documents-stats/products-stats/parts-stats/index/{ws}/accounts-stats/workspace-stats 仍只依赖 `get_current_user`，未检查 admin。
- 建议修复：统一替换为 `Depends(require_global_admin)`。
- 与前两轮关系：部分回归（P5-07 只修了 2 个，同类其余 8 个未覆盖）。

### P5-18 setUserAccess 用 UPSERT → 非成员用户触发 FK 500（应 400）
- 严重级：HIGH
- 类别：清单#2/#14（DTO 语义 + 事务安全）
- 文件：`app/services/user_manager.py:375-391`；`app/routers/workspace_memberships.py:179` | Java对照：`UserManagerBean.java:250-257` grantUserAccess 仅 UPDATE 已存在 membership（loadUserMembership→setReadOnly），不存在返回 null→400
- 证据：Python 用 `ON CONFLICT ... DO UPDATE`（UPSERT），对非成员用户（userdata 无行）触发 FK 违规：`violates foreign key constraint "fk_workspaceusermembership_member_login"`。冒烟：`PUT /workspaces/GD50/user-access {"member":{"login":"test3"},"membership":"READ_ONLY"}` → **500**（应 400）。
- 建议修复：先 SELECT 确认成员存在，不存在→400；存在→仅 UPDATE readonly（移除 INSERT 分支）。
- 与前两轮关系：新发现（P5-04 修 membership null 校验时引入 UPSERT 副作用）。

---

## MED

### P5-16 put_platform_options 返回 200+body 而非 204
- 严重级：MED
- 类别：清单#21
- 文件：`app/routers/admin.py:139-146` | Java对照：`AdminResource.java:298-303` `Response.noContent().build()`→204
- 建议修复：`return Response(status_code=204)`。
- 与前两轮关系：新发现。

### P5-08 WorkspaceDTO 多返回 admin 字段
- 严重级：MED
- 类别：清单#2
- 文件：`app/routers/workspaces.py:37-44`(_row_to_dict)、`admin.py:34-42`(_workspace_to_dict) | Java对照：`WorkspaceDTO.java` 仅 id/description/folderLocked/enabled
- 证据：Python 多 `admin` 字段（Java 无）；workspaces.py 还少 creationDate=None。
- 建议修复：移除 admin 字段或两处统一。
- 与前两轮关系：前轮未修。

### P5-20 setUserAccess 返回 UserDTO 多 membership 字段
- 严重级：MED
- 类别：清单#2
- 文件：`app/routers/workspace_memberships.py:189-195` | Java对照：`WorkspaceResource.java:468` map 到 UserDTO（login/name/email/language/workspaceId）
- 证据：Python 返回多 `"membership"` 字段；`GET /users/me` 也返回 `"membership": null`。
- 建议修复：移除 extra membership 字段。
- 与前两轮关系：新发现。

---

## LOW
- **P5-12** put_index 桩：`admin.py:188-196` 仅 `import elasticsearch` 后返回 `{"status":"accepted"}`，无实际索引操作。Java `indexManager.indexWorkspaceData`。建议标注桩或接真实 indexer。
- **P5-21** delete_account 级联不全：`account_manager.py:114-152` 处理 15 张表，但 information_schema 显示 33 张表 FK 到 account.login（documentrevision.author_login/partrevision.author_login/changeissue.author_login 等未 nullify）。用 `session_replication_role='replica'` 使删除成功但残留 dangling FK。建议删前 nullify 所有引用表或文档标注。新发现。

---

## 第2轮问题复核（已闭环）
P5-01（delete_workspace 补 folder 删除 `workspace_deletion.py:281-286` + replica 模式）、P5-02（workspaces.py import 已补，disk-usage 等 FA 自创端点已删）、P5-03（remove_from_group 返回被操作 group DTO）、P5-04（setUserAccess 校验 membership null→400 + 返 UserDTO，**但引入 P5-18 UPSERT 副作用**）、P5-05（setGroupAccess 返回 WorkspaceUserGroupMembershipDTO）、P5-06（my_memberships 单对象）、P5-09（deleteWorkspace 202）、P5-10/P5-11/P5-13/P5-14 均已修/前轮误判。

## 已核对一致的要点
| 要点 | 结论 |
|------|------|
| #1 裸SQL | workspaceusermembership/workspaceusergroupmembership/userdata/usergroupmapping 列名核实一致；"UPDATE SET 表不存在"是 ON CONFLICT DO UPDATE SET 脚本误报 |
| #6 权限 Depends | `deps.py` require_global_admin/require_workspace_admin 与 Java checkAdmin 逐行一致（usergroupmapping groupname='admin' + workspace.admin_login + usergroup_user JOIN 组检查）——但 P5-19/P5-07-REG 端点未调用 |
| #4 delete_workspace 级联 | 覆盖 60+ 表（workflow/pathdata/query/import/template/change/effectivity/folder/binaryresource），folder 已补，vault shutil.rmtree 正确 |
| #7 异常一致性 | service 层全领域异常，仅 organizations.py:164 router 层 HTTPException（可接受） |
| #15 路由接线 | service 均被正确调用，无 dead code |
| delete_role | 真实 db.delete+commit，非 stub（前轮误判澄清） |
