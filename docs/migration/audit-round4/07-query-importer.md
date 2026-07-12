# 域7 Query/Importer 查询与导入引擎 审计报告（第4轮）

> 生成日期：2026-07-12 ｜ 范围：`docdoku-plm-server-py` 查询/导入迁移代码 vs Java/Payara
> 方法：explore subagent 逐端点对照 + information_schema 核实 + SQL 注入面重点核查 + GD50 验证
> 基准 workspace = GD50 ｜ **只读审计，未做任何修复**

## 结论
**0 CRITICAL / 1 HIGH / 1 MED / 4 LOW**。查询引擎核心（SQL 注入防护、权限过滤、PBS 合并、查询保存）对齐良好。Importer 经第3轮重构后 `import_into_path_data` 已从 stub 变完整实现。本轮新发现 1 HIGH（PathData 导入缺实例级 canWrite 权限检查）。

---

## HIGH

### P7-14 import_into_path_data 缺实例级 canWrite 权限检查（权限绕过）
- 严重级：HIGH
- 类别：清单#6（权限绕过）
- 文件：`app/services/importer.py:378-379` | Java对照：`ImporterBean.java:527` createOrUpdatePathData 检查 `productInstanceManager.canWrite(workspaceId, productId, serialNumber)`，无权限时跳过该行 + 记错误
- 证据：Python 保留 TODO 注释「补 canWrite 实例级写权限检查（Java productInstanceManager.canWrite）；当前仅验证实例存在，未阻断无权限用户写入」。`productinstancemaster` 无 ACL 列（写权限由业务逻辑控制），当前任何认证用户可 POST `importType=pathdata` 写任意产品实例 PathData 属性。
- 建议修复：Phase1 循环调用实例级 canWrite 检查，无权限跳过 + errors 添加 AccessRightException。
- 与前两轮关系：新发现（第2轮该功能还是 stub，未涉及写入）。

---

## MED

### P7-15 import_into_parts checkout/checkin 内部独立 commit → 半成品状态
- 严重级：MED
- 类别：清单#14（事务与提交）
- 文件：`app/services/importer.py:239-270` | Java对照：`ImporterBean.java:418-483` bulkPartUpdate 单 EJB 事务（`@TransactionAttribute(REQUIRED)`）
- 证据：`svc.checkout()`(product_manager.py:459) / `svc.checkin()`(478) 各自 `db.commit()`。属性写入虽合并为循环外单次 commit（P7-03 子问题 A 已修），但 checkout 已即时持久化：零件 A checkout+write+checkin 全 commit → 零件 B checkout 失败 → A 已提交不可回滚。Java 整体成功或回滚。
- 建议修复：checkout/checkin 提供 `auto_commit=False`，由调用方统一管理事务。
- 与前两轮关系：P7-03 子问题延续（部分改善）。

---

## LOW
- **P7-05** `excel_parser.py:56-75` `_normalize_type` 用 `upper()` 宽松匹配，Java 类型大小写敏感。风险低（仅手写表头），可保留。前轮已知。
- **P7-06** query-export 用 openpyxl 生成 `.xlsx`（`parts.py:571-577`），Java 输出 `.xls`。已从 CSV 改善为真 Excel，格式仍不同。前轮改善。
- **P7-11** `query_rule.py:15` values `str()` 强转，前端发字符串无实际影响。前轮已知。
- **P7-12** `import_error`/`import_warning` 表无主键（`\d` 确认），`complete_import` 重复调用会重复插入。建议 INSERT 前 DELETE 幂等。前轮已知。

---

## 第2轮问题复核（多数闭环）
| 编号 | 原级 | 结论 |
|------|------|------|
| P7-01 | HIGH | ✅ 已闭环（`importer.py:325-464` import_into_path_data 完整实现：查实例→查/建 PathDataMaster→属性合并→auto_freeze） |
| P7-02 | LOW（证伪） | Java BomImporter 是接口 0 实现，`doBomImport` 死代码；Python `import_bom` 返回 NotSupported 是对齐行为 |
| P7-03 子A | MED | ✅ errors:[] 硬编码已修（`importer.py:272` 返回真实 errors 累积） |
| P7-04 | — | ✅ LOV 正则 `group(2)!="ListOfValues"` 立即报错，不 fall through |
| P7-07 | — | Python `MAX(iteration)` 子查询比 Java `size==iteration` 更健壮，无需修 |
| P7-08 | MED | ✅ `excel_parser.py:257-259` 处理 ids>values，多余 ID 建空值属性 |
| P7-09 | LOW | Java 也无 pathdata 分支，Python 支持 attributes/bom/pathdata 是扩展 |
| P7-10 | LOW | ✅ docstring 已更新；DB 核实 instanceattribute 34 行全有 dtype，0 NULL；dtype 分歧不存在 |

## 已核对一致的要点（重点：SQL 注入面）
| 要点# | 结论 |
|-------|------|
| #16 SQL注入 | **`query_executor.py:_safe_ident` 白名单正则 `^[A-Za-z_][A-Za-z0-9_]*$`；`_ATTR_PREFIXES` 静态列名映射；`_PR_VALID_COLS` frozenset 白名单；所有值走 :param；`importer._VALUECOL_WHITELIST` 校验动态列名。无 f-string 拼接用户可控字段名到 SQL 的风险（历史漏洞已修）** |
| #1 裸SQL | partrevision/partmaster/partiteration/partrevision_tag/partiteration_attribute/prdinstiteration_pathdatamstr/pathtopathlink/configurationitem_p2plink 列名核实一致 |
| #3 硬编码桩 | import_into_path_data 已实现；import_bom 对齐 Java 死代码；query POST 返回真实数据（Pinion 2010 查询正确） |
| #5 dtype完整性 | `_write_iteration_attributes` + `_sync_instance_attributes` 均写 dtype；PathData 经 path_data_service 写入也写 dtype |
| #11 path穿透 | `query_pbs.py:108-119` 仅 pathdata_rule+serial 时算 allowed_paths 逐路径过滤，对齐 Java |
| #17 端点覆盖 | 11 query+4 import（Java）→ 20 query+7 import（Python，含扩展）全对齐 |
| #21 状态码 | POST queries→200/GET imports→200/POST import→204/DELETE import→204 |

## 冒烟验证
| 测试 | Python(8009) | Java(8005) | 状态 |
|------|--------------|-----------|------|
| POST /workspaces/GD50/parts/queries (pm.number=Pinion 2010) | 200 → `[{"pr.partKey":"Pinion 2010-A"}]` | — | ✅ |
| GET /workspaces/GD50/parts/imports/test.xlsx | 200 → `[]` | 200 → `[]` | ✅ |
