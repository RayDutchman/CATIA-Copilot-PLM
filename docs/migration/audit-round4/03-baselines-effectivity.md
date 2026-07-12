# 域3 Baselines/Effectivity 基线与有效性 审计报告（第4轮）

> 生成日期：2026-07-12 ｜ 范围：`docdoku-plm-server-py` 基线/有效性迁移代码 vs Java/Payara
> 方法：explore subagent 逐端点对照 + information_schema 核实 + GD50 验证；主 agent 已直接核实 P3-11 表名
> 基准 workspace = GD50 ｜ **只读审计，未做任何修复**

## 结论
**1 CRITICAL / 0 HIGH / 2 MED / 3 LOW**。第2轮 3 HIGH（P3-01/02/03）全部闭环。本轮新发现 **1 个 CRITICAL（创建基线时替代/可选链接写错表 → 有非空链接时必 500）**。

---

## CRITICAL

### P3-11 create_baseline substituteLinks/optionalUsageLinks 写错表 + 当作 dict 处理 → 500
- 严重级：**CRITICAL**（原 subagent 判 HIGH，主 agent 复核升级：`str.get()` 触发 AttributeError 且写错表，属数据损坏/功能完全缺失）
- 类别：清单#1（裸 SQL 写入错误表）、#8
- 文件：`app/services/product_structure.py:947-964`（create_baseline） | Java对照：`ProductBaselineManagerBean.java:102-167` `baseline.addSubstituteLink(pathStr)`/`addOptionalUsageLink(pathStr)` → JPA 写 `productbaseline_substitutelink`/`productbaseline_optionallink`（`@ElementCollection`，列 `substitutelinks`/`optionalusagelinks`，类型路径字符串）
- 证据（**主 agent 已用 psql + 读码核实**）：
  - `productbaseline_substitutelink` 实际列：`productbaseline_id`、`substitutelinks`（varchar 255）。
  - Python 代码：
  ```python
  if substitute_links:
      for sl in substitute_links:               # sl 是路径字符串（Set[str]）
          db.execute(text("INSERT INTO partsubstitutelink ..."),
              {"cpn": sl.get("partNumber",""), "spn": sl.get("substitutePartNumber","")})
  ```
  `substitute_links` 来自 `spec.retained_substitute_links`（`Set[str]` 路径字符串），对 str 调 `.get()` → `AttributeError: 'str' object has no attribute 'get'` → 500；即便语法对，也写到 `partsubstitutelink`（零件替代实体表）而非 `productbaseline_substitutelink`（基线路径存储），表名/列名/语义全错。`optional_usage_links` 同理：Java 写 `productbaseline_optionallink`，Python 却 `UPDATE partusagelink.optional=true`。
- 影响：创建基线时传非空 substituteLinks/optionalUsageLinks 100% 500。Effectivity(2/3/4) 基线经 `_create_effectivity_baseline` 会走此路径。
- 建议修复：改为 INSERT `productbaseline_substitutelink.substitutelinks` / `productbaseline_optionallink.optionalusagelinks`（路径字符串），删除现有 partsubstitutelink/partusagelink 错误写入。
- 与前两轮关系：新发现（第2轮只审读取路径 P3-01，未审创建写入路径）。

---

## MED

### P3-03 put_effectivity 类型校验语义与 Java 不一致（残留）
- 严重级：MED（原 HIGH，"可清空下限"已堵，残留语义差异）
- 类别：清单#8
- 文件：`app/routers/effectivity.py:148-182` | Java对照：`EffectivityResource.java:109-142`、`EffectivityManagerBean.java:212-297`
- 证据：Python 已按 dtype/typeEffectivity 分派 + 下限非空校验（startDate/startNumber/startLotId）。但 Java PUT **始终要求**下限字段存在且非空（`pStartNumber==null → CreationException`），Python 仅当字段出现在 body 时才校验 → Python 接受不带下限字段的 PUT（保持原值），Java 拒收。边界：eff.dtype 为 None 且 body 无 typeEffectivity 时三分支都不匹配 → 无校验（实际 DB dtype 列非空）。
- 建议修复：PUT 强制要求下限字段存在。
- 与前两轮关系：前轮部分修，残留语义差异。

### P3-10 baseline P2P link 详情 sourceComponents/targetComponents 硬编码空
- 严重级：MED（原 LOW 升级：基线上 P2P 详情功能缺失）
- 类别：清单#8/#3
- 文件：`app/routers/product_baselines.py:237-242`（`_query_path_to_path_links`） | Java对照：`ProductBaselinesResource.java:336-361` getPathToPathLinkInProductBaseline 对每条 link 调 `decodePath()` 填 source/target
- 证据：Python 返回 `"sourceComponents": [], "targetComponents": []` 硬编码空数组。
- 建议修复：调 `svc.decode_path()` 解析 sourcePath/targetPath 填充。
- 与前两轮关系：新发现（本轮升级）。

---

## LOW
- **P3-09** delete_effectivity 先删 join 表（带 ws 过滤）再删 effectivity 主行，若 ws 不匹配 join 删 0 行但主行仍删 → FK 冲突 500（事务回滚，无数据损坏但报错不友好）。`effectivity_manager.py:92-100`。建议删前先查归属 ws。新发现。
- **P3-12** 死代码：`product_baselines.py:245-271` `_query_substitute_links`/`_query_optional_links` 定义后从未被调用（P3-01 修复后的遗留）。建议删除。新发现。
- **P3-13** `document_baseline_export.py:56` 用硬编码 `HTTPException(404)` 而非领域异常（export 路由层，可接受但记录）。

---

## 已核对一致的要点
| 清单# | 结论 |
|-------|------|
| #1 裸SQL | productbaseline/documentbaseline/documentcollection/baselineddocument/baselinedpart/partrevision_effectivity/effectivity/productbaseline_substitutelink/productbaseline_optionallink 逐列核实一致 |
| #2 DTO对齐 | ProductBaselineDTO/SummaryDTO/DocumentBaselineDTO/EffectivityDTO 逐字段对齐；**substituteLinks/optionalUsageLinks 读取路径已修为 List[str]（P3-01）**；configurationItemKey 已嵌套（P3-02） |
| #4 级联删除 | delete_baseline 级联 baselinedpart→baselineddocument→substitutelink/optionallink/p2plink→productbaseline→partcollection→documentcollection，完整 |
| #7 异常一致性 | service 层用领域异常（BaselineNotFoundException/EffectivityNotFoundException/CreationException 等），无硬编码 HTTPException（export 路由层 P3-13 例外） |
| #21 状态码 | GET→200/POST→201/DELETE→204/PUT→200；P3-04/P3-05 已修 |
| BFS校验 | `_validate_baseline_parts` 对齐 Java getLastCheckedInIteration/ReleasedPSFilter |

## 冒烟验证
`GET /workspaces/GD50/product-baselines` → 200，返回 1 条种子基线，substituteLinks/optionalUsageLinks 为空数组（读取路径类型正确）。`import app.main` OK。
