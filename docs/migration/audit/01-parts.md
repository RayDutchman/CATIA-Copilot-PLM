# Parts 零件域审计报告

> 审计员：explore subagent ｜ 日期：2026-07-11 ｜ 波次：1
> 范围：part.py / parts.py / part_files.py / part_templates.py / part_template_files.py / part_mapper.py / product_manager.py(零件部分)

## 问题 P-1
- 严重级：CRITICAL
- 类别：清单要点#9（深拷贝 vs 浅拷贝 clone 语义）
- 位置：`app/services/product_manager.py:1283-1297`、`:670-673`
- Java 对照：`ProductManagerBean.java:522`（`new ArrayList<>(...)` 浅拷贝，但 JPA 不级联删 M:N 目标）
- 证据：`_copy_iteration_files` 在 checkout 复制时，`part_iteration_usagelink` 直接复用同一 `component_id`（PartUsageLink 主键）。而 `__do_sync_components` 替换组件时会 `DELETE PartUsageLink WHERE id IN (old_link_ids)`。旧迭代仍引用同一 `component_id` → FK 违反（`partiteration_partusagelink.component_id → partusagelink.id`，RESTRICT）→ 500。
- 结论与建议：`_copy_iteration_files` 须深克隆 PartUsageLink（INSERT 新行、新建 component_id），或 `_sync_components` 移除对 PartUsageLink 的删除。**需主 agent 复核 FK 实际约束**。

## 问题 P-2
- 严重级：HIGH
- 类别：要点#17 + #3
- 位置：`app/routers/part.py:620-637`（retry_conversion）
- Java 对照：`PartResource.java:329-346`（retryConversion）
- 证据：Java 检查 nativeCADFile 存在→调用 converterService 实发转换→204，否则 400。Python 只把 Conversion 标 pending，不发 Kafka、不调 converter、无 nativeCADFile 检查，返回 `{"status":"retry_queued"}` 200。
- 结论与建议：补 nativeCADFile 检查→400，调用 send_conversion_order 发 Kafka→204。

## 问题 P-3
- 严重级：HIGH
- 类别：要点#17 + #21 + #3
- 位置：`app/routers/part.py:190-199`、`app/services/product_manager.py:918-955`（new_version）
- Java 对照：`PartResource.java:460-488`（createNewPartVersion）
- 证据：Java 接受 PartCreationDTO（description/workflowModelId/acl/roleMapping）→createPartRevision→204。Python 不接受 body，仅复制旧 revision description，忽略 workflowModelId/ACL/roleMapping，返回 200+DTO。
- 结论与建议：加 body、透传 workflow/acl/roleMapping、返回 204。

## 问题 P-4
- 严重级：MEDIUM
- 类别：要点#21（状态码对齐）
- 位置：part.py acl(166-175 实为 335-358)、publish(307-318)、unpublish(320-332)
- Java 对照：`PartResource.java` updatePartRevisionACL/publish/unpublish 均 204
- 证据：Python 三端点返回 200+body（AclIdDTO/PartRevisionDTO），Java 返回 204。
- 结论与建议：改 status_code=204。

## 问题 P-5
- 严重级：MEDIUM
- 类别：要点#6（权限检查）
- 位置：`app/routers/part.py:307-332`（publish/unpublish）
- Java 对照：`PartResource.java:639-679`
- 证据：Java 经 checkWorkspaceWriteAccess 需写权限；Python publish/unpublish 只 get_revision（读权限）无写权限检查。
- 结论与建议：加 check_write_access。

## 问题 P-6
- 严重级：MEDIUM
- 类别：要点#3 + #15
- 位置：`app/routers/parts.py:392-394`（post_queries 无 ws 前缀版）
- 证据：body 无 contexts / 首元素无 workspaceId 时 `return {"id": 0}` 假 ID。
- 结论与建议：无 workspace 应 400；核实路由前缀。

## 问题 P-7
- 严重级：MEDIUM
- 类别：要点#1（裸 SQL 跨 workspace JOIN）
- 位置：`app/services/part_mapper.py:184-208`（modificationnotification 查询）
- 证据：`LEFT JOIN partmaster pm ON pm.partnumber = mn.modified_partmaster_partnumber` 缺 workspace_id 条件；partmaster PK=(partnumber, workspace_id)，同号可跨 ws → 误匹配。
- 结论与建议：加 `pm.workspace_id = mn.modified_workspace_id`。

## 问题 P-8
- 严重级：MEDIUM
- 类别：要点#3（吞异常）
- 位置：`app/routers/parts.py:146-147`（search ES fallback `except Exception: pass`）
- 证据：吞所有异常静默降级 DB；Java 遇 IndexerNotAvailable 抛 500。
- 结论与建议：限定连接/超时异常，其余重抛。

## 问题 P-9 / P-12（LOW/风格）
- StatusDTO 多余 message 字段（P-9，无功能影响）；PartRevisionDTO extra='forbid' 反序列化偏严风险（P-12）。

## 问题 P-10 / P-11（LOW）
- P-10：`GET /parts/tags` FA=400 PY=404 —— 两端都无此端点，**框架路由差异，非 bug，已排除**。
- P-11：parts.py 与 part.py 的 router prefix 策略不一致（风格）。

## 已排除
- P-13：instanceattribute 缺 id → SERIAL 自增 + Python 各写入路径已写 dtype，机器扫描误报。

## 小结
| 严重级 | 数量 | 编号 |
|--------|------|------|
| CRITICAL | 1 | P-1 |
| HIGH | 2 | P-2、P-3 |
| MEDIUM | 6 | P-4~P-9 |
| LOW | 3 | P-10(排除)、P-11、P-12 |

整体评分 6.5/10：核心 CRUD 可用，checkout→update_components 深拷贝(P-1)、retryConversion(P-2)、newVersion body(P-3) 有功能性缺口。
