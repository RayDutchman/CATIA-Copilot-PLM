# 域8 横切/其他 审计报告（第4轮）

> 生成日期：2026-07-12 ｜ 范围：`docdoku-plm-server-py` 横切迁移代码（auth/share/tags/layers/lov/notifications/webhooks/attributes/platform + core 中间件 + WebSocket + SQL 注入面）vs Java/Payara
> 方法：explore subagent 逐端点对照 + information_schema 核实 + GD50 验证；主 agent 已核实 P8-11
> 基准 workspace = GD50 ｜ **只读审计，未做任何修复**

## 结论
**0 CRITICAL / 1 HIGH / 2 MED / 6 LOW**。第2轮 P8-01/02/04/05 已闭环，服务层 HTTPException 第3轮已清零。本轮新发现 1 HIGH（notification list_for_user 永久空结果）+ 2 MED。

---

## HIGH

### P8-11 notification list_for_user 永久返回空（功能完全失效）
- 严重级：HIGH
- 类别：清单#5/功能错误
- 文件：`app/services/notification_manager.py:25-31`（list_for_user） | Java对照：Java 无独立 list（通知嵌入 PartRevisionDTO），Python 自建端点过滤逻辑错误
- 证据（**主 agent 已用 psql 核实**）：
  ```python
  return db.query(ModificationNotification).filter(
      ModificationNotification.impacted_workspace_id == ws,
      ModificationNotification.acknowledged == False,
      ModificationNotification.ackauthor_login == login,   # ← BUG
  ).all()
  ```
  GD50 有 10 条未读通知，其 `ackauthor_login` 全为 **NULL**（确认人字段，未读时为空）。`ackauthor_login = 'test1'` 对 NULL 永不匹配 → 恒返回 `[]`。`ackauthor_login` 是"确认人"，不应用于未读过滤。
- 建议修复：移除 `ackauthor_login` 过滤条件（未读通知按 impacted_workspace_id + acknowledged=False 过滤，收件人应按订阅关系而非 ackauthor）。
- 与前两轮关系：新发现。

---

## MED

### P8-06 is_lov_deletable 缺实际零件迭代实例属性检查（残留）
- 严重级：MED
- 类别：清单#6（业务逻辑差异）
- 文件：`app/services/lov_manager.py:111-124` | Java对照：`LOVManagerBean.java:133-150` isLOVDeletable 检查 3 条件
- 证据：Java 检查①文档模板②零件模板③**实际零件迭代的实例属性模板**；Python 仅检查①instanceattributetemplate ②partiteration_pathdata_attr JOIN，**缺③ `partiteration_attribute JOIN instanceattribute(dtype='InstanceListOfValuesAttribute')`**。→ LOV 被实际零件迭代属性使用时仍可能被误删。
- 建议修复：追加对 partiteration_attribute→instanceattribute 的检查，对齐 Java findAllPartIterationFromLOV。
- 与前两轮关系：前轮已报 MED，修复不完整。

### P8-12 products.py 路由层硬编码 HTTPException（3 处）
- 严重级：MED
- 类别：清单#7（异常一致性）、#15
- 文件：`app/routers/products.py:111,171,197` | Java对照：Java ProductResource 抛领域异常（ConfigurationItemNotFoundException 等），由异常映射器转 HTTP
- 证据：line 111 `HTTPException(404, "Product structure not found...")` 应抛 ConfigurationItemNotFoundException；line 171 `HTTPException(404, "Product instance not found")` 应抛 ProductInstanceMasterNotFoundException（位置参数形式，工具盲区）；line 197 `HTTPException(404, str(e))` 吞原始异常应直接 raise。
- 建议修复：替换为领域异常，由全局 exception_handlers 统一转码。
- 与前两轮关系：新发现（工具位置参数盲区，人工 grep 发现）。

---

## LOW
- **P8-03** acknowledge 返回 200+DTO vs Java 204（`notifications.py:23-31`）。功能正确。前轮已知。
- **P8-07** UserLanguageMiddleware 每认证请求额外建独立 Session（`main.py:59-85`），耗 2 连接。前轮已知，连接池差异。
- **P8-08** WebhookDTO 多 workspaceId/webhookApp 字段（`webhook.py:12,16`），Java 无。前轮已知。
- **P8-09** create_tag 返回 201 vs Java 200（`tags.py:32`）。前轮已知。
- **P8-10/P8-13** getOrganization 无组织时 204 vs Java 200+null body（`organizations.py:36-38`）。前轮已知。
- （信息）P8-04 send_password_recovery 已写 passwordrecoveryrequest 表，但**未发邮件**——邮件族未迁移已知（loose-ends 第八节 sendPasswordRecovery）。

---

## 第2轮问题复核
| 编号 | 原级 | 结论 |
|------|------|------|
| P8-01 | MED | ✅ 已闭环（layers.py:76-78 仅清 layer_marker+删 layer，对齐 Java @ManyToMany 不级联删 marker） |
| P8-02 | HIGH | ✅ 已修复（organizations.py:148-183 完整实现 direction up/down，无效值 400） |
| P8-04 | MED | ✅ 已修复（auth.py:103-114 写 passwordrecoveryrequest；未发邮件属邮件族排期） |
| P8-05 | MED | ✅ 已修复（lov.py:45/76/93 均 check_write_access） |

## 已核对一致的要点
| 要点 | 结论 |
|------|------|
| 路由路径三方一致 | main.py router prefix 正确；WebSocket `/docdoku-plm-server-rest/ws` 对齐 nginx |
| WebSocket 参数注解 | `main.py:206` `websocket: WebSocket` 正确，不被误判 query |
| 中间件顺序 | ErrorCollector→UserLanguage→exception_handlers→URLDecode→TrailingSlash→CORS 逆序执行正确 |
| SQL注入面 | 所有 text() 走 :param，无 f-string 拼接用户输入 |
| 裸SQL表名列名 | tag/tagusersubscription/iterationchangesubscription/statechangesubscription/webhook/webhookapp/sharedentity/lov/lov_namevalue/layer/layer_marker/marker/modificationnotification/organization/organization_account/passwordrecoveryrequest 经 information_schema 核实（曾臆造的表名均已用真实表名） |
| 服务层HTTPException | 0 处违规（share_manager/organization_manager/webhook_manager/lov_manager 第3轮已清零）；share.py/organizations.py:164 router 层 HTTPException 属合理例外 |
| auth/login | MD5 + usergroupmapping 角色 + JWT 响应头 + admin 检测对齐 |
| platform/health/languages/timezones | 格式/值对齐 Java |
| error_collector | deque(500) + 跳过 /dev//docs/openapi/health，正确记录 req/res/user |
| vault路径 | `{ws}/parts/{pn}/{ver}/{it}/...` 对齐 |
| delete_webhook/share/lov 级联 | FK 顺序正确 |
| 回调鉴权 | conversion 回调用 JWT（get_current_user），长转换过期风险已知（REMINDERS 标注） |
