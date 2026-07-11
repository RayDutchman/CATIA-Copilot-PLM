# Baselines/Effectivity 域审计报告

> 审计员：explore subagent ｜ 日期：2026-07-11 ｜ 波次：2
> 范围：product_baselines.py / document_baselines.py / effectivity.py / effectivity_manager.py / product_structure.py(baseline 部分) / models/product/effectivity.py

## 问题 B-1
- 严重级：CRITICAL（**主 agent 已复核确认，见文末复核**）
- 类别：要点#1（ORM 列名 vs DB 真值）
- 位置：`app/models/product/effectivity.py`
- 证据：ORM 模型列映射 `start_lot=Column("startlot")` / `end_lot=Column("endlot")` / `creation_date=Column("creationdate")` / `type_effectivity=Column("type_effectivity")`，但 DB effectivity 表实际列为 startlotid/endlotid/startnumber/endnumber/startdate/enddate，无 creationdate/type_effectivity。
- 结论与建议：startlot→startlotid、endlot→endlotid，删除 creation_date/type_effectivity 伪列。

## 问题 B-2
- 严重级：CRITICAL
- 类别：要点#1（裸 SQL 列名）
- 位置：`app/routers/effectivity.py:138-142`、`app/services/effectivity_manager.py:60-64`
- Java 对照：`EffectivityManagerBean.java:92-95`
- 证据：`INSERT INTO partrevision_effectivity (workspace_id, ...)` 但 DB 实际列为 `partmaster_workspace_id`。GET(line 79)已用对的列名，INSERT 未修。
- 结论与建议：INSERT 改 `partmaster_workspace_id`。

## 问题 B-3
- 严重级：CRITICAL
- 类别：要点#1（裸 SQL 列名）
- 位置：`app/services/effectivity_manager.py:15-16,98-100`
- 证据：`SELECT/DELETE FROM effectivity WHERE id=:id AND workspace_id=:ws`，但 effectivity 表无 workspace_id 列（仅 configurationitem_workspace_id）。router delete 调用此 service 也会失败。
- 结论与建议：移除错误 workspace_id 过滤，改经 partrevision_effectivity 关联表验证归属。

## 问题 B-4
- 严重级：CRITICAL
- 类别：要点#4（级联删除）
- 位置：`app/services/product_structure.py:652-657`（delete_baseline）
- Java 对照：`ProductBaselineManagerBean.java:240-254`（JPA cascade）
- 证据：Python 仅 `db.delete(bl)`，遗漏 baselinedpart/partcollection/documentcollection/baselineddocument/productbaseline_substitutelink/optionallink/p2plink。workspaces.py:753-756 已有正确逻辑可参照。
- 结论与建议：补 7 条 DELETE。

## 问题 B-5
- 严重级：CRITICAL
- 类别：要点#3（逻辑缺失）
- 位置：`app/routers/document_baselines.py:115-167`
- Java 对照：`DocumentBaselineManagerBean.java:66-78,157-185`（snapshotDocuments）
- 证据：Python 直接插入用户提交的 baselinedDocuments，无类型过滤(RELEASED)/签出处理(LATEST)/已存在跳过/空集校验。
- 结论与建议：实现 snapshotDocuments 逻辑。
- **✅ 已修复（2026-07-12，批 7）**：`create_doc_baseline` 实现去重 + RELEASED（status IN 1,2 取末迭代）+ LATEST（签出感知，签出取 last-1）过滤；空集抛 `NotAllowedException66`（含 B-10）。对拍空集→403「您无法创建空文档集合」。

## 问题 B-6
- 严重级：HIGH
- 类别：要点#17
- 位置：`app/services/product_structure.py:531-534`（create_baseline）
- Java 对照：`ProductBaselineManagerBean.java:102-147`
- 证据：Java 支持 5 种 ProductBaselineType（LATEST/RELEASED/EFFECTIVE_DATE/SERIAL/LOT），Python 只处理 LATEST(0)/RELEASED(1)，缺 effectiveDate/effectiveSerialNumber/effectiveLotId 参数。
- 结论与建议：补三种 effectivity-based 基线类型。
- **✅ 已修复（2026-07-12，批 7）**：ProductBaselineType 枚举补 EFFECTIVE_DATE/SERIAL/LOT；3 个 create 路由映射 5 类型名 + 透传 effectiveDate/Serial/Lot；`create_baseline` 服务加参数 + `_fill_effectivity_baselined_parts`（裸 SQL 按 effectivity 选 revision，无匹配退化 LATEST）。**best-effort**：GD50 无 effectivity 数据、`PartRevision.effectivities` relationship 缺失，未在线验证。对拍创建 type=EFFECTIVE_DATE 成功、Payara 读回 `type:"EFFECTIVE_DATE"`。

## 问题 B-7
- 严重级：HIGH
- 类别：要点#2（DTO 字段）
- 位置：`app/routers/product_baselines.py:62-80`
- Java 对照：`ProductBaselineDTO.java` + `ProductBaselinesResource.java:222-224`
- 证据：detail 响应缺 configurationItemLatestRevision；多余 configurationItemWorkspaceId 非标准字段。
- 结论与建议：detail 补 configurationItemLatestRevision。
- **✅ 已修复（2026-07-12，批 7）**：detail 补 `configurationItemLatestRevision` + `hasObsoletePartRevisions`、删非标准 `configurationItemWorkspaceId`。**对拍 Payara(:8005) 确认 `configurationItemLatestRevision` 为 String 版本号（非对象）** → 连带把 summary DTO 及 `_ci_latest_revision` 由对象改字符串以对齐。detail keys 对拍一致（仅 `type` int-vs-string 为预存差异）。

## 问题 B-8 ~ B-12（MEDIUM）
- **B-8**(要点#4)：delete_baseline 未检查 productinstanceiteration 引用（Java isBaselinedUsed→EntityConstraintException16）。
- **B-9**(要点#11)：effectivity.py:164-180 `GET/PUT /effectivities/{id}` 缺 `/workspaces/{ws}` 前缀。`/parts/{key}/effectivities` 系列已对齐（排除）。
- **B-10**(要点#7)：document_baselines.py:123 空文档抛 HTTPException(400)，应 service 层抛 NotAllowedException66。**✅ 批 7 修复**（就地在 router 抛 NotAllowedException66，移到过滤后；本包无 doc-baseline service 文件）。
- **B-11**(要点#8)：effectivity.py:49-63 `_effectivity_to_dto` 双后备列名，建议统一 DB 真值列名。
- **B-12**(要点#7)：create_effectivity 未做三类型必填字段（startNumber/startDate/startLotId）校验，Java 抛 CreationException。

## 问题 B-13 ~ B-15（LOW）
- **B-13**(要点#2)：_bl_summary_dict 列表端点多返回 pathToPathLinks/optionalsParts，缺 substitutesParts。
- **B-14**(要点#6)：getAllBaselines/createBaseline 未显式调 workspace 权限（依赖 get_current_user，需核 deps.py）。
- **B-15**(要点#17)：P2P links types 端点路径前缀 `/product-baselines/{pid}/baselines/` 与 Java `/products/{ciId}/baselines/` 不一致→前端可能 404；缺 document-baseline export-files。**⚠️ 批 7 判定为误报**：Python 路径实为 `/workspaces/{ws}/product-baselines/{pid}/baselines/{bid}/path-to-path-links-types`，与 Java 类级 `@Path` 前缀对齐；document-baseline `export-files`（ZIP）已存在于 `routers/export/document_baseline_export.py`（忠实实现 `DocumentBaselineFileExportMessageBodyWriter`）。subagent 误加的重复 JSON-list 端点已由主 agent 回退。

## 已排除
- E-1 baseline BFS 校验 LATEST/RELEASED 逻辑正确。E-2 summary DTO 对齐无 422。E-3 DocumentBaseline 级联删除顺序正确。E-4 GET effectivity 用 partmaster_workspace_id 正确（历史 bug 已修）。E-5 baselinedpart 子查询列名正确。

## 小结
| 严重级 | 数量 |
|--------|------|
| CRITICAL | 5 | B-1~B-5 |
| HIGH | 2 | B-6、B-7 |
| MEDIUM | 5 | B-8~B-12 |
| LOW | 3 | B-13~B-15 |
| 已排除 | 5 | E-1~E-5 |

整体：基础 CRUD 端点覆盖较完整，但核心写路径 5 个 CRITICAL（effectivity ORM/INSERT 列名错、effectivity_manager workspace_id 过滤指向不存在列、baseline 删除缺级联、文档基线创建缺校验）。因 GD50 无 effectivity/baseline 数据未触发。**注：B-1/B-2/B-3 列名问题需主 agent 用 information_schema 二次核实后再定级。**
