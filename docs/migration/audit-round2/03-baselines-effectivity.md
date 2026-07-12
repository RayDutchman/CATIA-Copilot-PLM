# [Baselines/Effectivity] 审计报告（域3）

> 第二轮迁移代码审计 ｜ 只读代码对比 ｜ 基准 workspace = GD50（productbaseline/documentbaseline/effectivity 表当前均为空）

**总体结论**：0 CRITICAL / 3 HIGH / 3 MED / 4 LOW（经独立复核修订，3 HIGH 全部 CONFIRMED）

---

## 问题 P3-01
- 严重级：HIGH
- 复核：CONFIRMED。baseline substituteLinks/optionalUsageLinks 返回对象数组，Java 是路径字符串数组["1.1"]（ProductBaseline Set<String>）。第一轮只修了 config 域，baseline 域漏修。
- 类别：清单#2 / #8
- 文件：`app/routers/product_baselines.py:60-80`（_bl_summary_dict）、`245-271`
- Java对照：`ProductBaselinesResource.java:394-405`、`ProductBaseline.java:101-121`（substituteLinks: Set<String>）
- 证据：Java substituteLinks/optionalUsageLinks 返回路径字符串数组 `["1.1"]`；Python 返回对象数组 `[{"partNumber":...}]`，schema 也定义为 List[dict]。语义不一致。
- 建议修复：改查 productbaseline_substitutelink/optionallink 取路径字符串；新增 substitutesParts/optionalsParts 用解码逻辑填充。

## 问题 P3-02
- 严重级：HIGH
- 复核：CONFIRMED。EffectivityDTO 缺 configurationItemKey 嵌套对象（输出扁平 configurationItemNumber/workspaceId）；schema 有 ConfigurationItemKeyDTO 但端点无 response_model 未生效。
- 类别：清单#2 / #8
- 文件：`app/routers/effectivity.py:31-64`（_effectivity_to_dto）
- Java对照：`EffectivityResource.java:75-97`、`EffectivityDTO.java:49`（configurationItemKey）
- 证据：Java EffectivityDTO 有 configurationItemKey 嵌套对象（workspace+id），Python 设扁平 configurationItemNumber/workspaceId（schema 中不存在），configurationItemKey 从未赋值。前端读 configurationItemKey.id 得 undefined。
- 建议修复：设 `"configurationItemKey":{"workspace":...,"id":...}`。

## 问题 P3-03
- 严重级：HIGH
- 复核：CONFIRMED。put_effectivity 不按 typeEffectivity 分派/不校验下限字段，可静默清空 startDate；B-12 只修了 POST 未修 PUT。
- 类别：清单#8（行为对齐）
- 文件：`app/routers/effectivity.py:183-214`（put_effectivity）
- Java对照：`EffectivityResource.java:99-142`、`EffectivityManagerBean.java:212-297`
- 证据：Java PUT 按 typeEffectivity 分派并验证下限字段非空（Serial→startNumber/Date→startDate/Lot→startLotId，否则 CreationException）；Python 无条件写入，可静默清空 startDate。
- 建议修复：按 eff.dtype 做类型校验，下限字段不能清空。

## 问题 P3-04
- 严重级：MED
- 类别：清单#21（状态码）
- 文件：`app/routers/effectivity.py:183-214`
- Java对照：`EffectivityResource.java:99-142`（200 + DTO）
- 证据：Java PUT 返回 200+DTO，Python 返回 204 空 body。
- 建议修复：返回 200 + _effectivity_to_dto。

## 问题 P3-05
- 严重级：MED
- 类别：清单#21
- 文件：`app/routers/product_baselines.py:376-382`（delete_baseline，`/products/{ci}/baselines/{id}` 路径）
- Java对照：`ProductBaselinesResource.java:181-201`（204）
- 证据：返回 `{"status":"deleted"}`+200；同文件 delete_ci_baseline 已正确 204。
- 建议修复：加 status_code=204。

## 问题 P3-06
- 严重级：MED
- 类别：清单#17（端点覆盖缺口）
- 文件：`document_baselines.py`（无 export-files 端点）
- Java对照：`DocumentBaselinesResource.java:223-248`（exportDocumentFiles ZIP）
- 证据：Java 文档基线有 export-files（ZIP 打包），Python 仅产品基线有（product_baselines.py:437-466）。
- 建议修复：若前端用则补 GET .../document-baselines/{id}/export-files。

## 问题 P3-07
- 严重级：LOW（假报澄清）
- 类别：清单#2
- 证据：`ProductBaselineCreationDTO.java:35-147` 确认**无 author 字段**（author 服务层从 User 填充）；Python 端点用 body:dict 无 extra=forbid。**Phase-0 CRITICAL 为工具假报，无需修复。**

## 问题 P3-08
- 严重级：LOW
- 类别：清单#3（死代码）
- 文件：`app/services/documents/document_baseline_manager.py:60-77`（get_baselines/get_baseline）
- 证据：用 `WHERE workspace_id=:ws` 查 documentbaseline，但该表无 workspace_id 列（仅 author_workspace_id）。被调用会报错，但路由未使用（内联 SQL），为死代码。
- 建议修复：改 author_workspace_id 或删除该 service。

## 问题 P3-09
- 严重级：LOW
- 类别：清单#6 / #8
- 文件：`app/services/effectivity_manager.py:92-100`（delete_effectivity）
- Java对照：`EffectivityManagerBean.java:301-317`
- 证据：Python 直接 DELETE partrevision_effectivity，未验证 effectivity 归属；workspace 不匹配时 join 表未删但 effectivity 行被删 → FK 冲突 500（事务回滚，无损坏但报错不友好）。
- 建议修复：先验证归属再删。

## 问题 P3-10
- 严重级：LOW
- 类别：清单#8
- 文件：`app/routers/product_baselines.py:387-395`、`406-409`
- Java对照：`ProductBaselinesResource.java:312-362`
- 证据：baseline P2P detail 端点 sourceComponents/targetComponents 硬编码 []，Java 用 decodePath 填充。
- 建议修复：调 decode_path 填充。

---

## 已核对一致的要点
- #1 裸 SQL：effectivity/partrevision_effectivity/baselinedpart/baselineddocument/partcollection/documentcollection/pathtopathlink/productbaseline_p2plink 表名列名正确。
- #3：基线/效度路由无 return [] 吞异常。
- #4 级联：delete_baseline（product_structure.py:663-711）级联 baselinedpart→baselineddocument→substitutelink/optionallink/p2plink→productbaseline→partcollection→documentcollection；delete_doc_baseline 亦完整。
- #5 INSERT：partcollection/documentcollection/baselinedpart/baselineddocument NOT NULL 列均赋值，自增 id 无需手写。
- #7 异常：BaselineNotFound/EffectivityNotFound/NotAllowedException66 一致。
- #15 路由：Depends 注入正确，前缀一致。
- P3-11 BaselinedDocumentDTO（documentMasterId/version/iteration）已核对一致。
