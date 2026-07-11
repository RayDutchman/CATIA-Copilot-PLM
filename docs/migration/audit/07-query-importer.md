# Query/Importer 域审计报告

> 审计员：explore subagent ｜ 日期：2026-07-11 ｜ 波次：2
> 范围：query_executor.py / query_pbs.py / importer.py / importers/* / query_result.py / parts.py(queries 端点) / export/*

## SQL 注入面核查（要点#16）
逐条核对 16 处 f-string SQL：**值始终用绑定参数**，防护到位。列名 f-string 经 `_safe_ident()` 正则校验（`^[A-Za-z_][A-Za-z0-9_]*$`），阻断了引号/分号/注释符等注入字符。
- 大部分列名来自硬编码 dict（安全）。
- **MEDIUM 风险**：query_executor.py:181 `f"pr.{sub.lower()}"`、:202 `f"pm.{sub.lower()}"` 仅正则校验无列名白名单——恶意用户可构造合法标识符访问不应查询的列。建议加显式列名白名单。
- importer.py:71 valcol 经 `_VALUECOL_WHITELIST` 白名单（安全）。

## 问题 Q-1
- 严重级：CRITICAL
- 类别：要点#6（权限后处理）
- 位置：`app/services/query_executor.py:312-345`（run_part_query）
- Java 对照：`ProductManagerBean.java:2802-2825`（searchPartRevisions）
- 证据：Java 有 isCheckoutByAnotherUser→detach+removeLastIteration 隐藏签出状态。Python 只做检入过滤+读权限过滤，缺 checkout-by-another-user 隐藏 → 信息泄露。
- 结论与建议：补 checkout 隐藏分支。

## 问题 Q-2
- 严重级：CRITICAL
- 类别：要点#1（裸 SQL 列名）
- 位置：`app/services/query_executor.py:214`
- Java 对照：`PartRevisionQueryDAO.java:208-210`（getAuthorPredicate）
- 证据：author.* 分支硬编码 `acc.name`，查询 author.email/author.language 时会错误用值查 name 列。account 表确有 email/language 列。
- 结论与建议：改 `_cmp(f"acc.{sub}", ...)` + `_safe_ident(sub)`。

## 问题 Q-3
- 严重级：CRITICAL
- 类别：要点#17（端点缺口）
- 位置：`app/routers/parts.py:501-531`（query_export GET）
- Java 对照：`PartsResource.java:362-410`（POST exportCustomQuery + GET exportExistingQuery）
- 证据：Python 只有 GET query-export 接受简单参数，不支持 POST body 传完整 QueryDTO（规则树/PBS context），也缺导出已保存查询端点。
- 结论与建议：query_export 改 POST 接 JSON body；新增 GET /parts/queries/{queryId}/format/{export}。

## 问题 Q-4
- 严重级：HIGH
- 类别：要点#17（端点缺口/桩）
- 位置：`app/services/importer.py:270-296`（import_into_path_data / import_bom）
- Java 对照：`ImporterBean.java:165-214`
- 证据：两方法均硬编码 `return {"succeed": False, ...}` 桩。Java doPathDataImport(~60行) + doBomImport(~85行) 有完整实现。注释称"Java 亦无实现"不实。
- 结论与建议：PathData 导入应优先实现；BOM 依赖 BomImporter 插件。

## 问题 Q-5
- 严重级：HIGH
- 类别：要点#3（假成功桩）
- 位置：`app/routers/parts.py:383-394`（post_queries 无 ws 前缀版）
- 证据：无法推断 workspace 时 `return {"id": 0}` 假成功。
- 结论与建议：返回 400。（与波1 Parts 域 P-6 同一处，合并）

## 问题（MEDIUM）
- **Q-7**(要点#1)：query_result.py:126-127 `pr.lifeCycleState`/`pr.linkedDocuments` 始终返回空串，Java 从 workflow 模型派生。
- **Q-8**(要点#16)：query_executor.py:107-108 operator 不在 op_sql dict 时 KeyError→500，应 fallback `1=1`。
- **Q-9**(要点#2)：parts.py:373 post_workspace_query response_model=list 不精确；export=CSV 返回 400（Java 支持 CSV）。
- **Q-10**(要点#12)：query_executor.py:43-54 _parse_date 不处理时区，Java 携带 pTimeZone 做偏移，跨时区日期区间可能偏移一天。

## 问题（LOW）
- **Q-11**(要点#1)：query_executor.py:181 _pr_leaf fallback 对 pr.checkOutUser/pr.author 等 relationship 字段生成非法列名→500。加白名单。
- **Q-12**(要点#1)：export/query_result.py:46 export_query_as_json 绕过 query_executor 规则引擎，只做简单过滤，不等价 Java 导出。

## 已排除
- FE-1 import_error/import_warning 表存在列名正确。FE-2 _sync_instance_attributes 已写 dtype（要点#5 已解决，建议更新 checklist）。FE-3 11 前缀路由完整（8 attr-* + 8 pd-attr-*）。FE-4 operator 映射/date 区间等价。FE-5/FE-6 querycontext/query 列名正确。FE-7 query_selects.selects 列名正确。FE-8 partiteration_attribute 表列名正确。FE-9 usergroupmapping 表存在。Q-6 _sync_instance_attributes 已写 dtype（排除）。Q-13 query 删除级联顺序正确（排除）。

## 小结
| 严重级 | 数量 |
|--------|------|
| CRITICAL | 3 | Q-1、Q-2、Q-3 |
| HIGH | 2 | Q-4、Q-5 |
| MEDIUM | 4 | Q-7、Q-8、Q-9、Q-10 |
| LOW | 2 | Q-11、Q-12 |
| 已排除 | 9+2 | FE-1~9、Q-6、Q-13 |

整体：Query 执行引擎核心（operator 映射、11 前缀路由、属性 EXISTS、权限/检入过滤）质量较高，与 PartRevisionQueryDAO 对齐良好。主要缺陷：checkout 隐藏遗漏(Q-1)、author.* 列名错误(Q-2)、导出端点架构断裂(Q-3)、两个导入桩(Q-4)。SQL 注入面基本安全但列名白名单可加强。

---

## 修复状态（2026-07-12，FIX-PLAN 批次 5）

- ✅ **Q-1**（CRITICAL）：`run_part_query` 对被他人签出的 revision 隐藏末迭代。**主 agent 修数据丢失隐患**：`iterations` 关系 `cascade="all, delete-orphan"`，直接 `pop()` 会在 save=true 的 commit 时真删末迭代 → 改为先预加载 part_master + `db.expunge(pr)`（对齐 Java em.detach）再 pop。alice 签出 + save=true 验证迭代数不变。
- ✅ **Q-2**（CRITICAL）：author.* 分支 `acc.name` 硬编码 → `acc.{_safe_ident(sub)}`，支持 email/language/name。
- ✅ **Q-11**（LOW）：`_pr_leaf` fallback 加 `_PR_VALID_COLS` 白名单，非白名单返回 `1=1` 防 500。
- ⏳ **留批 6**：Q-3（query-export 改 POST+补导出已存查询，涉及 parts.py，避免与其它 parts.py 修改并行冲突）。
- ⏳ **未纳入**：Q-4（导入桩）、Q-5/P-6（批 6）、Q-7~Q-10/Q-12（MEDIUM/LOW）。
