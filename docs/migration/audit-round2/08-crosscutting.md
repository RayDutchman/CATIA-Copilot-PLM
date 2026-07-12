# [横切/其他] 审计报告（域8）

> 第二轮迁移代码审计 ｜ 只读代码对比 ｜ 基准 workspace = GD50
> 范围：auth/share/tags/layers/lov/notifications/webhooks/attributes/platform/organizations + 中间件 + core + ws + vault

**总体结论**：整体迁移质量较好，中间件链正确，裸 SQL 基本核实，无 SQL 注入，WebSocket 已对齐。0 CRITICAL / 1 HIGH / 5 MED / 3 LOW（经独立复核修订）。（复核后仅 P8-02 move_member 维持 HIGH；P8-01 降 MED、P8-03 降 LOW）

---

## 问题 P8-01
- 严重级：MED（原 HIGH，复核调整）
- 复核：SEVERITY-ADJUST→MED。delete_layer 子查询顺序 bug 真实（第②步死代码），但 Java @ManyToMany 无 cascade 也不删 marker，当前运行结果反而与 Java 一致，属死代码质量问题非功能偏差。
- 类别：清单#4（级联删除）
- 文件：`app/routers/layers.py:76-80`（delete_layer）
- Java对照：`LayerResource.java:143-151` → productService.deleteLayer JPA cascade
- 证据：先 `DELETE FROM layer_marker WHERE layer_id`，再 `DELETE FROM marker WHERE id IN (SELECT marker_id FROM layer_marker WHERE layer_id)` —— 第二步子查询从已清空的 layer_marker 取，必然空集，marker 永不删除 → 孤立 marker 残留。
- 建议修复：交换①②顺序（先删 marker 再删 layer_marker）。

## 问题 P8-02
- 严重级：HIGH
- 复核：CONFIRMED。organizations move_member 忽略 direction 只上移（Java 按 up/down 双向 + 无效值 400）。down 功能完全缺失。
- 类别：清单#6 / 功能缺失
- 文件：`app/routers/organizations.py:195-237`（move_member）
- Java对照：`OrganizationResource.java:224-249`（direction up/down）
- 证据：Java moveMember 按 direction 双向移动，无效 direction 返回 400；Python 忽略 direction，只实现上移。
- 建议修复：加 direction 参数实现 moveMemberDown。

## 问题 P8-03
- 严重级：LOW（原 HIGH，复核调整）
- 复核：SEVERITY-ADJUST→LOW。acknowledge 返回 200+DTO（Java 204），纯响应形态差异，功能正确，客户端不会失败。
- 类别：清单#15（响应形态）
- 文件：`app/routers/notifications.py:92-100`（acknowledge）
- Java对照：`ModificationNotificationResource.java:69-77`（204）
- 证据：Java 返回 204 无 body，Python 返回 200+完整通知 DTO。
- 建议修复：返回 Response(status_code=204)。

## 问题 P8-04
- 严重级：MED
- 类别：清单#3（stub/功能缺失）
- 文件：`app/routers/auth.py:99-107`（send_password_recovery）
- Java对照：`AuthResource.java:165-197`
- 证据：send_password_recovery 从不写 passwordrecoveryrequest 表（直接返回 204），但 execute_recover 的 token 模式查该表 → token-based 恢复永远失败，仅 login+newPassword 模式可用。
- 建议修复：send_password_recovery 创建 passwordrecoveryrequest（UUID token）。

## 问题 P8-05
- 严重级：MED
- 类别：清单#6（权限检查）
- 文件：`app/routers/lov.py:48-61`（create）、`94-104`（delete）
- Java对照：`LOVManagerBean.java:82-119`（checkWorkspaceWriteAccess）
- 证据：LOV create/update/delete 只经 deps 读权限校验，无显式写权限检查（Java 区分读/写）。当前模型影响有限，引入只读成员则暴露。
- 建议修复：加 checkWorkspaceWriteAccess。

## 问题 P8-06
- 严重级：MED
- 类别：清单#6 / 业务逻辑差异
- 文件：`app/services/lov_manager.py:67-72`（isLOVDeletable）
- Java对照：`LOVManagerBean.java:131-150`
- 证据：Java 检查 3 条件（doc 模板/part 模板/实际零件迭代使用），Python 只检查 instanceattributetemplate 模板级引用，缺实际零件迭代使用检查 → 可删正被引用的 LOV（无 FK 违约但语义不一致）。
- 建议修复：加 partiteration_attribute→instanceattribute→LOV 回溯检查。

## 问题 P8-07
- 严重级：MED
- 类别：清单#12（中间件）
- 文件：`app/main.py:67-74`（UserLanguageMiddleware）
- 证据：每个带 JWT 请求额外创建独立 SessionLocal()，与 get_db 分离，每请求耗 2 连接，高并发下连接池（10+20）可能耗尽。
- 建议修复：记录为已知差异，或复用请求级 session。

## 问题 P8-08 / P8-09 / P8-10
- 严重级：LOW
- P8-08：schemas/misc/webhook.py WebhookDTO 多 workspaceId/webhookApp 字段（Java 用 WebhookAppParameterDTO），设计差异，标注即可。
- P8-09：tags.py:42-58 create_tag 返回 201，Java 返回 200 → 建议改 200。
- P8-10：organizations.py:23-38 getOrganization 无组织时 Python 返回 204+None，Java 返回 200+null → 建议对齐 200+null。

---

## 已核对一致的要点
- **SQL 表名/列名**：lov/lov_namevalue/tag/tagusersubscription/tagusergroupsubscription/webhook/webhookapp/sharedentity/layer/layer_marker/marker/oauthprovider/instanceattributetemplate/modificationnotification 全部 \d 核实一致。
- **SQL 注入面**：所有 text() 用 :param 绑定，f-string 仅用于代码常量表名/列名，无注入。
- **中间件注册顺序**：ErrorCollector→UserLanguage→exception_handlers→URLDecode→TrailingSlash→CORS，逆序执行正确（ErrorCollector 包裹全部，UserLanguage 路由前设语言）。
- **WebSocket**：路径 /docdoku-plm-server-rest/ws（main.py:200）与 nginx upgrade 对齐；handler `websocket: WebSocket` 注解正确。
- **auth/login**：MD5(MD5) 密码验证 + JWT 响应头返回 + admin 角色检测对齐。
- **share 公开访问**：sharedentity 查询 + MD5 密码 + 过期 + entity-token 对齐。
- **platform/health**：路径 + {executionTime,status} 对齐。
- **languages/timezones**：静态列表 ["fr","en","ru","zh"] + zoneinfo 一致。
- **attributes**：JOIN instanceattribute→partiteration_attribute→partiteration + dtype 映射 + _filter_attributes 去重对齐。
- **exceptions.py**：ApplicationException→404/403/400/500 映射与 Java ExceptionMapper 一致。
- **vault 路径**：{ws}/parts/{pn}/{ver}/{it}/{sub_type}/{file} 无多余 geometry/，一致。
- **tag 删除级联**：清理 7 张关联表一致。
- **error_collector**：deque(500) 跳过 /dev//docs/openapi/health。
- **i18n**：_SafeFormatter 安全处理缺失占位符。
- **database.py**：get_db 异常回滚+finally close + pool_pre_ping。
