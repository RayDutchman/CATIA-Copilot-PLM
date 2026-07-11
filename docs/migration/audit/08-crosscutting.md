# 横切/其他域审计报告

> 审计员：explore subagent ｜ 日期：2026-07-11 ｜ 波次：2
> 范围：auth.py / share.py / tags.py / layers.py / lov.py / notifications.py / webhooks.py / attributes.py / platform.py / 各 service / main.py 中间件 / vault.py / ws/

## 问题 X-1（原 1-1）
- 严重级：CRITICAL（**主 agent 需二次核实 sharedentity 列名**）
- 类别：要点#1（裸 SQL 列名）
- 位置：`app/routers/share.py:80-84`
- Java 对照：`SharedResource.java:165` + SharedEntity.java（expireDate→expiredate）
- 证据：DB sharedentity 列为 `expiredate`（无下划线），Python SQL 用 `expire_date` → 运行时 `column "expire_date" does not exist`。使 `/shared/{uuid}/documents` 和 `/shared/{uuid}/parts` 每次 500。
- 结论与建议：`expire_date`→`expiredate`。

## 问题 X-2（原 1-2）
- 严重级：CRITICAL
- 类别：要点#6（权限逻辑顺序）
- 位置：`app/routers/share.py:206-207`（和 245-246）
- Java 对照：`SharedResource.java:100-116`
- 证据：Python 先 `_check_workspace_member`（非成员即抛异常）再检查 public_shared，Java 总是先尝试公开共享（无需认证）再检查认证。非成员用户无法访问公开共享资源。
- 结论与建议：`_check_workspace_member` 移到 public_shared 检查之后。

## 问题 X-3（原 1-3）
- 严重级：HIGH
- 类别：要点#1（裸 SQL 列名）
- 位置：`app/services/share_manager.py:15,26`
- 证据：`SELECT se.* FROM sharedentity se WHERE se.password = :uuid`——用 password 列匹配 UUID 参数；line 26 `SELECT expire ...` 列名也错。该 service 未被 router 直接调用（死代码），但错误存在。
- 结论与建议：改 `WHERE se.uuid = :uuid`，`expire`→`expiredate`。

## 问题 X-4（原 1-4）
- 严重级：HIGH
- 类别：要点#20（回调鉴权）
- 位置：`app/routers/part.py:153-157`（conversion_callback）
- 证据：回调端点 `Depends(get_current_user)` 要求有效用户 JWT，上传时把用户 JWT 传给 Kafka；CAD 转换耗时数分钟，JWT 过期后回调 401，阻塞 CAD 预览。
- 结论与建议：引入服务间认证（API key/长效 token）或放宽此端点过期检查。

## 问题 X-5（原 1-5）
- 严重级：HIGH
- 类别：要点#4（级联删除）
- 位置：`app/routers/tags.py:83-98`（delete tag）
- Java 对照：`TagResource.java:146-153`
- 证据：FK 约束 NO ACTION。Python 只删 tag 行，若被 documentrevision_tag/partrevision_tag/change*_tag 引用 → FK 违规 500。
- 结论与建议：先清理各 *_tag 关联表。

## 问题（MEDIUM）
- **X-6**(要点#10)：vault.py 缺 `part_geometry_path`（test_vault.py 导入失败，确认真实缺失非测试过时）。converter.py:44/binary_storage.py:126 内联构造可用但不一致。vault fullName 格式 `{ws}/parts/{pn}/{ver}/{it}/{filename}`（无 geometry/ 子目录）。建议补函数并替换内联。
- **X-7**(要点#17)：notifications.py 缺 GET 列表端点（notification_manager.list_for_user 已存在未暴露）。
- **X-8**(要点#2)：auth.py:110-133 execute_recover 用 `body.get("password")` 取值，前端发 `newPassword` → 取空串写库。应用 PasswordRecoverDTO。
- **X-9**(要点#21)：tags.py:61-80 create_tags 批量返回列表(200/201)，Java 返回 204。
- **X-10**(要点#17)：webhooks.py create/update 缺 SNS 支持（Java configureWebhook 按 appName 路由 Simple/SNS）。标注已知限制。
- **X-11**(要点#6)：auth.py:19-55 login 缺 OAuth ProvidedAccount 检查（Java 拒绝 ProvidedAccount 密码登录 403）。
- **X-12**(要点#1)：notification_manager.py:26-29 list_for_user 未按当前用户过滤（缺 `AND ackauthor_login=:login`）→ 隐私泄漏。

## 问题（LOW）
- **X-13**(要点#2)：share.py:139-140 等 entity-token 生成格式与 Java createSharedEntityToken/createEntityToken 不一致，前端用 token 请求后续文件可能 401/403。

## 已排除
- LOV 表名：DB 确为 lov/lov_namevalue，Python 全部正确。
- 中间件：4 个全接线且顺序正确（TrailingSlash→URLDecode→UserLanguage→ErrorCollector 最外层）。
- WebSocket：main.py:201 及 ws/endpoint.py 的 WebSocket 类型注解正确。
- part_geometry_path：确认真实缺失（见 X-6），非测试过时。

## 小结
| 严重级 | 数量 |
|--------|------|
| CRITICAL | 2 | X-1、X-2 |
| HIGH | 3 | X-3、X-4、X-5 |
| MEDIUM | 8 | X-6~X-12 |
| LOW | 1 | X-13 |

整体：端点骨架完成，中间件接线正确，WebSocket 修复到位。但 share 模块 2 个 CRITICAL（SQL 列名错 + 公开共享权限逻辑错）导致端点不可用，conversion 回调鉴权有架构缺陷。修复 CRITICAL+HIGH 共 5 项后此域基本可用。

---

## 修复状态（2026-07-12，FIX-PLAN 批次 6）

- ✅ **X-5**（HIGH）delete tag：先清 5 张 *_tag 关联表 + tagusersubscription/tagusergroupsubscription（主 agent 补 2 张订阅表），再裸 SQL 删 tag 行（避免 ORM M:N secondary 重新 INSERT 导致 FK 冲突）。**主 agent 关键发现**：真正生效的 delete_tag 在 workspaces.py（重复路由遮蔽 tags.py），已移除重复路由使 tags.py 生效。
- ✅ **X-7**（MED）notifications.py 新增 GET 列表端点。
- ✅ **X-8**（MED）auth recover：`password` → `newPassword`。
- ✅ **X-9**（MED）create_tags(/multiple) → 204，body 改 TagListDTO `{tags:[...]}`。
- ✅ **X-12**（MED）notification_manager.list_for_user 补 `ackauthor_login == login` 过滤。
- ✅ **X-6**（MED）vault.py 补 part_geometry_path（test_vault 现可收集通过）。**主 agent 回退** subagent 对 converter/binary_storage 的路径改动（其 `geometry/{quality}.glb` 与生产扁平 UUID 存储不符，会破坏 3D 预览）。
- ⏳ 未纳入：X-4（回调 JWT，架构性）、X-10（SNS）、X-11（OAuth）、X-13（LOW）。
