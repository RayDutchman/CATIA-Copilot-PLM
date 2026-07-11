# Workspace / 用户 / 权限 / 管理域审计报告

> 审计员：explore subagent ｜ 日期：2026-07-11 ｜ 波次：1
> 范围：workspaces.py / workspace_memberships.py / users.py / user_groups.py / accounts.py / organizations.py / roles.py / admin.py / workspace_manager.py / user_manager.py / account_manager.py / organization_manager.py / security_service.py

## 机器扫描 3 个 UPDATE error 核实结论
**已排除——全部解析器误报。** 三处均为 `INSERT ... ON CONFLICT DO UPDATE SET <col>`，解析器误把列名当表名。DB 核实 `workspaceusermembership.readonly`、`tagusersubscription.oniterationchange`、`tagusergroupsubscription.oniterationchange` 均合法列，表名均存在。

## 问题 W-1
- 严重级：CRITICAL
- 类别：要点#4（级联删除完整性）
- 位置：`app/routers/admin.py:208-217`（delete_workspace）
- Java 对照：`AdminResource.java:338-366` → `WorkspaceManagerBean.deleteWorkspace:94-101` → `WorkspaceDAO.removeWorkspace:127-475`（40+ 表）
- 证据：admin.py 仅 `DELETE FROM workspace WHERE id=:id`（1 行）。`workspaces.py:609-893` 的同名端点有完整级联，但 admin.py 完全没做。
- 结论与建议：抽取共享级联函数，admin.py 调用之。否则管理员删 ws 产生大量孤儿数据 + 重建 FK 冲突。

## 问题 W-2
- 严重级：CRITICAL
- 类别：要点#4（级联删除）
- 位置：`app/routers/admin.py:138-143`（delete_account）
- Java 对照：`UserManagerBean.removeUser:117-129`
- 证据：Python 仅删 credential/userdata/usergroupmapping/account，未删 organization_account/gcmaccount/passwordrecoveryrequest/providedaccount/workspaceusermembership/workspaceusergroupmembership/role_user/tagusersubscription/workspace.admin_login 引用。
- 结论与建议：按依赖顺序级联清理或用 replica 模式。

## 问题 W-3
- 严重级：CRITICAL
- 类别：要点#4（级联删除）
- 位置：`app/services/workspace_manager.py:55-64`（delete_workspace）
- 证据：与 admin.py:208 同样的单行删除 stub。当前 routers/workspaces.py 内联了完整级联未用此 service，但此 stub 存在即定时炸弹。
- 结论与建议：删除此 stub 或重写为调用共享级联函数，或 raise NotImplementedError。

## 问题 W-4
- 严重级：HIGH
- 类别：要点#3（硬编码桩）
- 位置：`app/routers/accounts.py:79-90`（put_gcm/delete_gcm）
- Java 对照：`AccountResource.java:224-257`
- 证据：两端点 `return Response(status_code=204)` 无操作。Java 写/删 gcmaccount 表。
- 结论与建议：实现 gcmaccount INSERT/DELETE。

## 问题 W-5
- 严重级：HIGH
- 类别：要点#6 + #4
- 位置：`app/services/user_manager.py:94-101`（remove_user_from_workspace）
- Java 对照：`UserManagerBean.removeUser:117-129` → UserDAO.removeUser:109-111
- 证据：Python 只删 userdata/usergroupmapping，未处理 workspaceusermembership 和 group 关联 → 孤儿 membership，后续 enable/disable 可能违反唯一约束。
- 结论与建议：补 DELETE workspaceusermembership + 迭代 usergroup 删关联。

## 问题 W-6
- 严重级：HIGH
- 类别：要点#5 + #13
- 位置：`app/routers/workspaces.py:495-550`（create_workspace）
- Java 对照：`WorkspaceManagerBean.createWorkspace:157-172`
- 证据：(1) enabled 策略缺失——Java 按 workspaceCreationStrategy，ADMIN_VALIDATION 时 enabled=false；Python 恒 TRUE(525)。(2) 未校验命名约定 NamingConvention.correct。(3) Java @Asynchronous，Python 同步（仅记录）。
- 结论与建议：读 platformoptions.workspacecreationstrategy 设 enabled；加命名校验。

## 问题 W-7
- 严重级：HIGH
- 类别：要点#15（路由/接线）
- 位置：`app/routers/workspace_memberships.py:99-102`（add_user）
- Java 对照：`WorkspaceResource.java:380-394`（@QueryParam("group")）
- 证据：Java group 在 URL 查询参数、login 在 body；Python 从 body.get("group") 取。前端按 Java 发 `?group=xxx` 时 Python 读到 None，用户永远直接加入 ws 而非工作组。
- 结论与建议：改 `group: str = Query(None)`。

## 问题 W-8 ~ W-14（MEDIUM）
- **W-8**(要点#6)：workspace_memberships.py:62-66 my_memberships 实现路径与 Java 不同但等价，非 bug。
- **W-9**(要点#7)：user_manager.py:48-60 delete_group 只查成员数，未查 ACL 约束（Java hasACLConstraint）。补 aclusergroupentry 检查。
- **W-10**(要点#2)：workspace_user_membership.py:13 多余 permission 字段 + extra='forbid'，前端误传会 422。确认后移除。
- **W-11**(要点#4)：user_manager.py:48-60 delete_group 直接 db.delete(g)，未先删 workspaceusergroupmembership，可能 FK 错。
- **W-12**(要点#17+#15)：workspace_manager.py create_workspace service 版与 router 内联版重复且不对齐（不建 ES 索引/userdata/membership），无人调用但可误用。
- **W-13**(要点#20)：admin.py:370-378 put_index 仅 import elasticsearch 返回 202，不做实际索引。假成功桩。
- **W-14**(要点#1)：organization_manager.py:54-56 `UPDATE account SET organization_name` —— account 表无 organization_name 列（应写 organization_account 表）。死代码未被调用。

## 问题 W-15 ~ W-17（LOW）
- **W-15**(要点#6)：workspaces.py:54-76 list_workspaces 不过滤 enabled，显示 disabled ws。
- **W-16**(要点#17)：admin.py 缺 OAuth provider CRUD（GET/POST/PUT/DELETE /admin/providers）+ PUT /admin/index-all。
- **W-17**(要点#8)：workspaces.py:162-163 磁盘统计遍历文件系统，Java 查 DB，高负载下可能不一致。

## 小结
| 严重级 | 数量 |
|--------|------|
| CRITICAL | 3 | W-1、W-2、W-3 |
| HIGH | 4 | W-4、W-5、W-6、W-7 |
| MEDIUM | 7 | W-8~W-14 |
| LOW | 3 | W-15~W-17 |
| 已排除 | 3 | UPDATE error×3 |

整体：workspaces.py 级联删除已完整修复(~140表)，tag subscription 对齐良好。**3 个 CRITICAL 必修**：admin.py 删 ws 无级联(W-1)、admin.py 删账户不完整(W-2)、workspace_manager.py delete_workspace 单行 stub(W-3)。加 GCM 空桩(W-4)、add_user 参数错位(W-7)、enabled 策略(W-6)。

---

## 修复状态（2026-07-12，FIX-PLAN 批次 6）

- ✅ **W-4**（HIGH）put_gcm/delete_gcm 实现 gcmaccount 幂等写/删 + 204。
- ✅ **W-5**（HIGH）remove_user_from_workspace 补 workspaceusermembership + workspaceusergroupmembership 清理，usergroupmapping 限本 ws 组。
- ✅ **W-6**（HIGH）create_workspace 按 platformoptions.workspacecreationstrategy(1=ADMIN_VALIDATION) 设 enabled=false + is_valid_name 命名校验。
- ✅ **W-7**（HIGH）add_user group 改 Query(None) 参数。
- ✅ **W-9/W-11**（MED）delete_group 补 aclusergroupentry 检查 + 先删 workspaceusergroupmembership。
- ✅ **W-14**（MED）删除 organization_manager 2 个死代码方法（写不存在的 account.organization_name 列）。
- ✅ **主 agent**：移除 workspaces.py 与 tags.py 重复的 5 个 tag 路由（原遮蔽 tags.py 使 X-5/X-9 成死代码）。
- ⏳ 未纳入：W-8/W-10/W-12/W-13（MED）、W-15/W-16/W-17（LOW）。
