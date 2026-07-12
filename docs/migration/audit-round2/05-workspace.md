# [Workspace/Users/权限] 审计报告（域5）

> 第二轮迁移代码审计 ｜ 只读代码对比 ｜ 基准 workspace = GD50

**总体结论**：2 CRITICAL / 5 HIGH / 4 MED / 3 LOW（经独立复核修订）。workspace 级联删除漏删 folder 表是数据完整性风险；多个端点存在 NameError 运行时崩溃；返回格式多处与 Java 不对齐。

---

## 问题 P5-01
- 严重级：CRITICAL
- 复核：CONFIRMED。workspace_deletion.py 全文 293 行无 DELETE FROM folder；DB 确认 GD50 有 2 行 folder 会永久残留；第一轮 W-1 修复遗漏了抽取函数本身。维持 CRITICAL。
- 类别：清单#4（级联删除）
- 文件：`app/services/workspace_deletion.py`（全文）
- Java对照：`WorkspaceDAO.java:353-362`
- 证据：Java 显式 UPDATE Folder parentFolder=NULL + DELETE FROM Folder；Python 17 步删除**无 DELETE FROM folder**。GD50 有 folder 数据。replica 模式让事务提交成功但 folder 永久残留为孤儿。
- 建议修复：删 workspace 前先 UPDATE folder parentfolder=NULL 再 DELETE folder（LIKE 'ws/%'）。

## 问题 P5-02
- 严重级：CRITICAL
- 复核：CONFIRMED。workspaces.py 顶部 import 确无 Path/settings/indexer_manager，disk-usage-stats/PUT index/POST workspaces 首次调用即 NameError 崩溃。维持 CRITICAL。
- 类别：清单#3（运行时崩溃）
- 文件：`app/routers/workspaces.py:148,161`（disk_usage_stats）；另 241 reindex_workspace、422 create_workspace 引用 indexer_manager
- Java对照：`WorkspaceResource.java:656-666`
- 证据：使用 `Path(...)` 与 `settings` 但文件顶部未 import `from pathlib import Path` / `from app.core.config import settings`；indexer_manager 亦未导入 → 运行时 NameError。
- 建议修复：补 import；indexer_manager try/except 延迟导入。

## 问题 P5-03
- 严重级：HIGH
- 复核：PARTIAL（维持 HIGH）。非 IndexError 崩溃（group 必存在）；实为返回 list_groups()[0] 任意 group 而非被操作 group（Java 返回被操作 group）。严重性描述从"崩溃"改为"返回错误 DTO"。
- 类别：清单#3（运行时崩溃）
- 文件：`app/routers/workspace_memberships.py:149`（remove_from_group）
- Java对照：`WorkspaceResource.java:504-512`
- 证据：`return _group_to_dict(list_groups(db,ws)[0])`，无组时 [0] IndexError；Java 返回被操作 group。
- 建议修复：返回被操作 group 或 204。

## 问题 P5-04
- 严重级：HIGH
- 复核：CONFIRMED。setUserAccess 返回 {"status":"ok"} 而非 UserDTO + 缺 membership null→400。
- 类别：清单#2 / #21
- 文件：`app/routers/workspace_memberships.py:235`（setUserAccess）
- Java对照：`WorkspaceResource.java:455-469`
- 证据：Java 返回 UserDTO 且 membership==null 时 400；Python 返回 `{"status":"ok"}` 无校验。
- 建议修复：返回 UserDTO + membership null → 400。

## 问题 P5-05
- 严重级：HIGH
- 复核：CONFIRMED（行号更正）。实际端点在 user_groups.py:141（非 workspace_memberships.py:141）；setGroupAccess 返回 {"status":"ok"} 而非 DTO。
- 类别：清单#2
- 文件：`app/routers/workspace_memberships.py:141`（setGroupAccess）
- Java对照：`WorkspaceResource.java:483-490`
- 证据：Java 返回 WorkspaceUserGroupMemberShipDTO，Python 返回 `{"status":"ok"}`。
- 建议修复：返回完整 DTO。

## 问题 P5-06
- 严重级：HIGH
- 复核：CONFIRMED。my_memberships 返回列表（Java 单对象）+ 多 permission 字段（Java DTO 无）。
- 类别：清单#2 / #8
- 文件：`app/routers/workspace_memberships.py:61-66`（my_memberships）
- Java对照：`WorkspaceMembershipResource.java:98-113`
- 证据：Java 返回单个 WorkspaceUserMemberShipDTO，Python 返回列表且空时 []；Python DTO 多 Java 不存在的 permission 字段。
- 建议修复：改返回单个 DTO。

## 问题 P5-07
- 严重级：HIGH
- 复核：CONFIRMED。admin.py get_platform_options/get_index 缺认证/admin 检查（Java 类级 @RolesAllowed(ADMIN_ROLE_ID)）。
- 类别：清单#15（接线/权限）
- 文件：`app/routers/admin.py:263`（get_platform_options）、`409-412`（get_index）
- Java对照：`AdminResource.java:58-64`（类级 @RolesAllowed(ADMIN_ROLE_ID)）
- 证据：get_platform_options 不调 _require_admin；get_index 无 current_user 参数（无认证）。任何登录用户可访问管理端点。
- 建议修复：补 _require_admin + 认证。

## 问题 P5-08
- 严重级：MED
- 类别：清单#2
- 文件：`app/routers/workspaces.py:42-50,424-431`（_row_to_dict/create_workspace）
- Java对照：`WorkspaceDTO.java`（仅 id/description/folderLocked/enabled）
- 证据：Python 多返回 admin、creationDate(固定 None) 噪音字段。
- 建议修复：移除 admin/creationDate 或文档标注为扩展。

## 问题 P5-09
- 严重级：MED
- 类别：清单#21（状态码）
- 文件：`app/routers/workspaces.py:490-499`（deleteWorkspace）
- Java对照：`WorkspaceResource.java:281-297`（202 Accepted，@Asynchronous）
- 证据：Java 返回 202（异步），Python 204（同步），大工作区可能超时。
- 建议修复：至少改 202；长期异步化。

## 问题 P5-10
- 严重级：MED
- 类别：清单#2
- 文件：`app/routers/workspace_memberships.py:85-94`（my_group_memberships）
- Java对照：`WorkspaceMembershipResource.java:139-165`
- 证据：Python 缺 readOnly 字段（Java DTO 有 workspaceId/memberId/readOnly）。
- 建议修复：JOIN workspaceusergroupmembership 取 readonly。

## 问题 P5-11
- 严重级：MED
- 类别：清单#2
- 文件：`app/routers/workspaces.py:91-111`（getReachableUsers）
- Java对照：`WorkspaceResource.java:216-239`
- 证据：Python ReachableUserDTO 缺 language 和 workspaceId（Java UserDTO 有）。
- 建议修复：改 List[UserDTO] 或补字段。

## 问题 P5-12
- 严重级：LOW
- 类别：清单#3（stub）
- 文件：`app/routers/admin.py:401-405`（put_index）
- 证据：不执行真实索引，只 import elasticsearch 后返回 accepted。
- 建议修复：ES 未配置返回 501 或文档标注。

## 问题 P5-13
- 严重级：LOW
- 类别：清单#3（代码风格）
- 文件：workspaces.py:28-39 + workspace_memberships.py:23-34 + users.py:19-29 + user_groups.py:19-29 + roles.py:17-28
- 证据：`_check_workspace_admin`/`_check_is_admin` 逐字重复定义 5 处。
- 建议修复：抽取到 core/deps.py 或 security_service.py。

## 问题 P5-14
- 严重级：LOW（Phase-0 STUB 澄清）
- 类别：清单#19
- 文件：`app/services/security_service.py:52-63`（delete_role）
- 证据：audit_write_stubs 标 DELETE /roles STUB，但代码 `db.delete(role)+commit` 正确，**非 stub**。机器测试误判（删后读回与初始态对比）。
- 建议修复：无需改代码，stub 脚本验证逻辑需改进。

---

## 已核对一致的要点
- #1 UPSERT 表名列名：workspaceusermembership/tagusersubscription/workspaceusergroupmembership 的 ON CONFLICT 列名正确。Phase-0 3 个 "UPDATE SET 表不存在" 为**已知假报**（ON CONFLICT DO UPDATE SET）。
- #8 usergroupmapping.groupname nullable，Python 总传具体值，不写 NULL。
- #4 admin.py delete_account 覆盖 14 表 + FK 禁用 + workspace admin_login 置空（Python 扩展）。
- #6 create_workspace ADMIN_VALIDATION 策略对齐。
- user_manager.add_user/remove_user_from_workspace 与 Java 对齐。
- #17 域5 端点覆盖完整；loose-ends 提到的 disk-usage/users/{login}/in-progress 已无残留。
