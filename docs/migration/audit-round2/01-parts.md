# [Parts] 审计报告（域1）

> 第二轮迁移代码审计 ｜ 只读代码对比（Java 源 vs Python 迁移）｜ 基准 workspace = GD50

**总体结论**：0 CRITICAL / 1 HIGH / 7 MED / 3 LOW（经独立复核修订）。最严重为 PUT /tags 500 根因、get_latest_revision 缺权限检查、filter_by_baseline 返回类型不匹配。

---

## 问题 P1-01
- 严重级：MED（原 CRITICAL，复核调整）
- 复核：SEVERITY-ADJUST→MED。set_tags 传 dict 会 500 属实，但前端只用 POST add_tag（已适配 _extract_tag_labels）+ DELETE，从不调 PUT set_tags，潜在缺陷不被触发。
- 类别：清单#2（DTO 字段对齐）+ #3（假成功）
- 文件:行号：`app/routers/part.py:213-220`（`set_tags`）
- Java对照：`PartResource.java:725-742`（savePartTags）
- 证据：PUT /tags 走 `svc.set_tags`，其内部 `for label in labels: Tag(label=label)`，但前端发 `{"tags":[{"label":"tag1"}]}`，labels 是 list[dict]，把 dict 存入 varchar(100) → **HTTP 500**。POST add_tag 正确用了 `_extract_tag_labels(body)` 适配，set_tags 遗漏。
- 建议修复：set_tags 也用 `_extract_tag_labels(body)` 解析成 list[str]。

## 问题 P1-02
- 严重级：LOW（初判 CRITICAL，经核对 SQL 列名一致后降级）
- 类别：清单#2 / 性能
- 文件:行号：`app/routers/parts.py:30-40`、`app/services/part_mapper.py:174-267`
- Java对照：`PartsResource.java:123-142`
- 证据：list_parts 逐 revision 查 notifications（N+1）；列名对 information_schema 核实均一致（`modified_partmaster_partnumber` 等），功能正确，仅性能。
- 建议修复：批量查询 notifications。

## 问题 P1-03
- 严重级：MED（原 HIGH，复核调整）
- 复核：SEVERITY-ADJUST→MED。返回 PartRevisionDTO 列表 vs Java 单 PartIterationDTO 属实，但前端未调用该端点（grep 无匹配）。
- 类别：清单#2（DTO 字段对齐）
- 文件:行号：`app/routers/part.py:578-628`（filter_by_baseline）
- Java对照：`PartsResource.java:306-331`（filterPartMasterInBaseline）
- 证据：Java 返回单个 `PartIterationDTO`（`mapPartIterationToPartIterationDTO`），Python 返回 `[map_revision(...)]`（完整 revision DTO 列表）。响应结构完全不同。
- 建议修复：返回 `PartIterationDTO`（用 map_iteration）。

## 问题 P1-04
- 严重级：HIGH
- 复核：CONFIRMED。Java getLatestPartRevision 有 canAccess→hasPartRevisionReadAccess→403，Python 无任何 ACL 检查，信息泄露漏洞。维持 HIGH。
- 类别：清单#6（权限检查）
- 文件:行号：`app/routers/part.py:370-379`（get_latest_revision）
- Java对照：`PartsResource.java:333-360`（`productService.canAccess` 无权限则 403）
- 证据：Python 缺 ACL 权限检查，任何认证用户都能取最新 revision。
- 建议修复：补 check_read_access，无权限 403。

## 问题 P1-05
- 严重级：MED（原 HIGH，复核调整）
- 复核：SEVERITY-ADJUST→MED。缺 SubResource DELETE 文件路径属实，前端调会 404，但仅影响 checkin 期间取消已上传文件（低频，上传/下载/重命名正常）。
- 类别：清单#17（端点覆盖缺口）
- 文件:行号：`app/routers/part.py`（整体）
- Java对照：`PartResource.java:558-581`（removeFile，路径 `/iterations/{partIteration}/files/{subType}/{fileName}`）
- 证据：Java 同时注册 SubResource 路径与 PartBinaryResource 路径；Python 只实现 `/files/...` 路径。前端若调旧路径 404。
- 建议修复：确认前端路径，必要时补端点。

## 问题 P1-06
- 严重级：MED
- 类别：清单#2/#8（NULL 容忍度）
- 文件:行号：`app/schemas/part/part_revision.py:27` + map_revision
- Java对照：`PartRevisionDTO` status 字段（RevisionStatus 枚举，nillable）
- 证据：`partrevision.status` nullable int，Python `STATUS_MAP.get(None,"WIP")` 把 NULL 变 "WIP"，Java 可能输出 null。
- 建议修复：status 为 None 时返回 None。

## 问题 P1-07
- 严重级：MED
- 类别：清单#2/#8
- 文件:行号：`app/schemas/part/part_revision.py:8`、`part_mapper.py:238-267`
- Java对照：`PartRevisionDTO` tags（String[]，无 nillable）
- 证据：Python `tags: List[str]=[]` 始终返回 []，Java 可能返回 null。
- 建议修复：改 `Optional[List[str]]=None` 或确认 Java 始终赋值。

## 问题 P1-08
- 严重级：MED
- 类别：清单#17（端点覆盖缺口/字段忽略）
- 文件:行号：`app/routers/part.py`（newVersion）
- Java对照：`PartResource.java:448-489`（createNewPartVersion）
- 证据：Java newVersion 处理 description/workflowModelId/acl/roleMapping 四字段，Python 只处理 description，其余忽略 → 新版本无工作流/ACL/角色映射。
- 建议修复：补 workflowModelId/acl/roleMapping 传递。

## 问题 P1-09
- 严重级：MED
- 类别：清单#6（权限检查）
- 文件:行号：`app/routers/part.py:239-254`（add_tag）、`product_manager.py:1133-1151`
- Java对照：`PartResource.java:744-778`
- 证据：add_tag service 调 get_revision 不传 current_user_login → 跳过写权限检查，任何用户可给任意零件加标签。
- 建议修复：补 check_write_access。

## 问题 P1-10
- 严重级：LOW
- 类别：清单#2
- 文件:行号：`app/schemas/part/cad_instance.py:8`
- 证据：Python CADInstanceDTO 含 m00-m22（Java DTO 无，来自 entity 映射），属额外扩展，向后兼容无害。
- 建议修复：无需修复。

## 问题 P1-11
- 严重级：LOW
- 类别：清单#5（INSERT 列完整性）
- 文件:行号：`app/services/product_manager.py:948-974`（_sync_instance_attributes）
- 证据：INSERT instanceattribute 缺 `partmaster_workspace_id`/`partmaster_partnumber`（nullable FK），Java JPA 自动写。影响 query_executor 按 partmaster 过滤时不可见（partiteration_attribute join 不受影响）。
- 建议修复：INSERT 时补两列。

---

## 已核对一致的要点
- #1 裸 SQL：`partrevision_tag`/`partiteration_attribute`/`instanceattribute`/`partusagelink_cadinstance`/`cadinstance`/`modificationnotification`/`pusagelink_psubstitutelink` 表名列名全部与 information_schema 吻合。
- #9 深拷贝：`_copy_iteration_files` 对 instanceattribute/partusagelink/cadinstance 均 INSERT...RETURNING 新行，clone 语义正确。
- #3 硬编码桩：Parts 路由未发现 return [] 吞异常。
- #15 路由接线：路径与 Java 一致，Depends 注入正确。
- #16 SQL 注入：列名/表名硬编码白名单，值走绑定参数。
- #14 事务：update_iteration 用 begin_nested 保护，undo_checkout try/except。
- #7 异常一致性：NotAllowedException/AccessRightException 同名。
- #4 级联：undo_checkout 清理 partiteration_attribute/partusagelink/binres/geometry/documentlink/pathdata_attr。
- #10 vault 路径：`{ws}/parts/{pn}/{ver}/{it}/{subType}/{file}` 无 geometry/，一致。
- #13 同步/异步：conversion callback 两侧均同步。
