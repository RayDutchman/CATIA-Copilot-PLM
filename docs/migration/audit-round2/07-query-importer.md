# [Query/Importer] 审计报告（域7）

> 第二轮迁移代码审计 ｜ 只读代码对比 ｜ 基准 workspace = GD50

**总体结论**：Query 引擎核心（SQL 编译/权限过滤/checkout 隐藏/查询保存）对齐良好，SQL 注入面已用白名单+绑定参数；Importer 零件属性导入/Excel 解析基本对齐。0 CRITICAL / 1 HIGH / 7 MED / 4 LOW（经独立复核修订；P7-02 证伪降 LOW）。

---

## 问题 P7-01
- 严重级：HIGH
- 复核：CONFIRMED。import_into_path_data 是 stub；Java doPathDataImport 有完整实现（+PathDataAttributesImporterImpl），确为迁移缺口。
- 类别：清单#3（stub/功能缺失）
- 文件：`app/services/importer.py:270-282`（import_into_path_data）
- Java对照：`ImporterBean.java:485-514`（doPathDataImport 完整实现）
- 证据：直接返回 NotSupported stub；Java 有完整 PathData 导入流程。
- 建议修复：移植 doPathDataImport + createOrUpdatePathData + bulkPathDataUpdate。

## 问题 P7-02
- 严重级：REFUTED 证伪→LOW（原 HIGH）
- 复核：REFUTED→LOW。Java BomImporter 仅接口无任何 implements，selectBomImporter 恒返回 null，doBomImport 是死代码；loose-ends 已记载"Java BomImporter 本无实现"。Python stub 是对齐行为。
- 类别：清单#3（stub/功能缺失）
- 文件：`app/services/importer.py:284-309`（import_bom/dry_run_import_bom）
- Java对照：`ImporterBean.java:657-741`（doBomImport 完整实现）
- 证据：均返回 NotSupported；ext/bom_importer.py 只有 ABC 无实现。Java 有完整 BOM 导入。
- 建议修复：移植 doBomImport + getOrCreatePartMaster + createUsageLink + ExcelParser BOM 解析。

## 问题 P7-03
- 严重级：MED（原 HIGH，复核调整）
- 复核：SEVERITY-ADJUST→MED。per-part commit 真实存在，但原报告"Java 全成全败"不准确（Java ApplicationException 无 @ApplicationException 注解，被 catch 后事务照样提交，行为与 Python 相近）。附带发现独立 bug：import_into_parts 返回 errors:[] 丢弃 checkout 失败错误。
- 类别：清单#14（事务/半成品状态）
- 文件：`app/services/importer.py:179-216`（import_into_parts）
- Java对照：`ImporterBean.java:418-483`（bulkPartUpdate 单事务）
- 证据：写入循环内逐零件 db.commit()（line 209），中途失败已提交零件不回滚但整体标记 succeed=False → DB 与记录不一致。Java 单事务全成或全败。
- 建议修复：改单次批量 commit 或入口 begin_nested，失败整体回滚。

## 问题 P7-04
- 严重级：MED
- 类别：清单#8（LOV 表头解析分歧）
- 文件：`app/services/importers/excel_parser.py:142-156`
- Java对照：`ExcelParser.java:311-322`
- 证据：LOV 正则匹配但 group(2)!="ListOfValues" 时 Java 报 ATTRIBUTE_TYPE_NOT_FOUND 且不设 headFormat；Python `pass` fall through 到 ATT 正则贪婪匹配 → 静默错误解析。
- 建议修复：该情况立即 add error 并 return，不 fall through。

## 问题 P7-05
- 严重级：MED
- 类别：清单#8（类型校验容差）
- 文件：`app/services/importers/excel_parser.py:56-75`（_normalize_type）
- Java对照：`ExcelParser.java:49,326`
- 证据：Java 类型大小写敏感（须 "Text"），Python upper() 后匹配（"text" 也通过）。Python 更宽容。
- 建议修复：文档标注差异（通常宽容无害）。

## 问题 P7-06
- 严重级：MED
- 类别：清单#8（导出格式）
- 文件：`app/routers/parts.py:540-562`（query_export）
- Java对照：`PartsResource.java:784-794`（ExcelGenerator XLS）
- 证据：Java exportType=xls 输出真正 .xls；Python 输出 CSV（application/csv, TSR.csv）。
- 建议修复：用 openpyxl 生成 XLSX，或文档标注 CSV 简化。

## 问题 P7-07
- 严重级：MED（实为 Python 改进）
- 类别：清单#8
- 文件：`app/services/query_executor.py:152-164`
- Java对照：`PartRevisionQueryDAO.java:213-216`
- 证据：Java 用 size(partIterations)==iteration 取末迭代（假设连续），Python 用 max(iteration) 子查询。迭代号有间隙时 Java 丢匹配，Python 正确。
- 建议修复：无需修复，记录为已知差异（Python 更健壮）。

## 问题 P7-08
- 严重级：MED
- 类别：清单#8（多值拆分）
- 文件：`app/services/importers/excel_parser.py:234-238`
- Java对照：`ExcelParser.java:400-407,826-865`
- 证据：values>ids 时两侧都报 MISSING_ATTRIBUTE_ID（对齐）；但 ids>values 时 Java 为多余 ID 创建空值属性，Python 跳过。
- 建议修复：确认前端依赖，必要时 Python 补空值属性。

## 问题 P7-09
- 严重级：MED
- 类别：清单#17（端点覆盖缺口）
- 文件：`app/routers/parts.py`（整体）
- Java对照：`PartsResource.java`
- 证据：post_import 只允许 attributes/bom，不支持 importType=pathdata（Java 有）；filterPartMasterInBaseline / getLatestPartRevision 端点（注：域1 P1-03/域1 已覆盖 filter_by_baseline 存在，此处指 query 视角）。
- 建议修复：post_import 增 pathdata 分支（待 P7-01 后）。

## 问题 P7-10
- 严重级：LOW
- 类别：清单#5（注释误导）
- 文件：`app/services/importer.py:40-43`（docstring）
- 证据：docstring 称 product_manager._sync_instance_attributes 不写 dtype，但实际 product_manager.py:949-958 通过 _infer_attribute_dtype **写了 dtype**。**清单#5 设计分歧假设不成立**。DB 核实 instanceattribute 56 行全有 dtype，无 NULL。
- 建议修复：更新 docstring 删除错误声称。（重要：修正 loose-ends 记录的"设计分歧"）

## 问题 P7-11 / P7-12 / P7-13
- 严重级：LOW
- P7-11：query_rule.py:15 values str() 强转，前端始终发字符串，无实际影响。
- P7-12：import_error/import_warning 表无主键，complete_import 重试可能重复行 → 建议 INSERT 前 DELETE 幂等。
- P7-13：parts.py:335-346 额外 _query_admin_flag 检查，与 Java 逻辑等价，无需修复。

---

## 已核对一致的要点
- **#16 SQL 注入**：query_executor 列名走 _safe_ident 白名单 + _ATTR_PREFIXES/_PR_VALID_COLS 固定映射，值走绑定参数；importer 动态列名 _VALUECOL_WHITELIST；parts._delete_query_by_id 表名来自硬编码元组。**无注入风险。**
- #1 裸 SQL：query/queryrule/queryrule_values/query_selects/query_order_by/query_grouped_by/querycontext/import/import_error/import_warning/instanceattribute/partiteration_attribute/pathdata* 全部核实正确。
- #5 查询保存：_save_query_rule 用 nextval('queryrule_qid_seq') 递归插入 + 同名先删后建。
- #5 dtype：两处路径都写 dtype，分歧不存在（见 P7-10）。
- #6 权限：run_part_query 实现 checkout 隐藏末迭代 + 必须有已检入迭代 + check_read_access，对齐 searchPartRevisions。
- #8 属性 EXISTS：_attr_exists 用 EXISTS+JOIN 按 dtype+name 过滤，优于 Java cross join。
- #8 merge_attributes：更新/新建/DuplicateEntry/AttributeNotFound + LOV 索引解析对齐。
- #8 ExcelParser：表头正则/comment 回退/多值/类型校验/重复检测全对齐。
- #8 Import 记录 CRUD：列名/FK/类型核实一致。
- #15 路由：11 query + 5 import + export 端点路径对齐。
