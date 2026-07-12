# 迁移代码审计（第4轮）总报告 — 00 Index

> 生成日期：2026-07-12 ｜ 范围：`docdoku-plm-server-py` 全量迁移代码 vs Java/Payara（`docdoku-plm-server`）**代码对比**
> 方法：主 agent 跑 4 个机器脚本收集线索（阶段0）→ 8 域 explore subagent 分 2 波并行逐端点对照 Java 源 + information_schema 核实 + GD50 有数据环境验证（阶段1）→ **主 agent 直接用 psql/读码核实所有 CRITICAL/关键 HIGH（P2-14/P3-11/P8-11/P5-19/P1-13）**→ 汇总去重定级（阶段2）
> 基准 workspace = GD50（当前为 `seed_test_data.py` 种子数据）｜ **只审计不修复**
> 分域报告：`01-parts.md` `02-products.md` `03-baselines-effectivity.md` `04-documents.md` `05-workspace.md` `06-workflow-change-tasks.md` `07-query-importer.md` `08-crosscutting.md`
> **重要背景**：本轮审计的是**第3轮大重构（分支 `fix/audit-remediation`，17 commits）之后**的代码——第3轮把 ~350 处 router 内联 DB 操作迁进 service 层。本轮重点复核该重构是否引入回归/副作用，并对前两轮问题做闭环复核。
> ⚠️ 路由接线专项报告位于 `docs/migration/audit-round3/15-routing-wiring.md` + `FIX-PLAN.md`（非本目录），本轮与其对齐去重，不覆盖。

---

## 〇、修复状态（2026-07-12 更新，见 `FIX-PLAN.md`）

**✅ 全部 2 CRITICAL + 13 HIGH + 16 MED 已修复并部署**（22 LOW 及已知计划外项不列入本轮，用户确认"修到 MED"）。分 4 批执行，commit：`0d087a1`(B1) / `84d9229`(B2) / `c69d251`(B3) / `d46e7ea`(B4)。全程 pytest **282 passed / 1 skipped 零回归**，CRITICAL 经 GD50 造数据复测，权限项经 non-admin/admin smoke 对拍。镜像已 rebuild 持久化。
**未修（保留）**：P2-08（linkType 重构风险高）、P1-06（status NULL 待 Payara 对拍）、P8-03（LOW+测试依赖）、22 LOW、邮件族 P6-01/P6-08、P5-12、P5-21。

---

## 一、问题总计（经主 agent 复核定级）

| 域 | CRITICAL | HIGH | MED | LOW | 说明 |
|----|:---:|:---:|:---:|:---:|----|
| 1 Parts | 0 | 2 | 3 | 2 | P1-13 remove_tag 缺权限、P1-12 newVersion 描述写旧版本 |
| 2 Products | **1** | 2 | 3 | 2 | **P2-14 CRITICAL** PathData INSERT 列名错 |
| 3 Baselines/Effectivity | **1** | 0 | 2 | 3 | **P3-11 CRITICAL** 基线替代/可选链接写错表 |
| 4 Documents | 0 | 2 | 1 | 1 | mark_obsolete + tags 缺权限；14 项前轮问题全闭环 |
| 5 Workspace/用户/权限 | 0 | 3 | 3 | 2 | P5-19/P5-07-REG 权限缺口、P5-18 UPSERT 500 |
| 6 Workflow/Change/Tasks | 0 | 2 | 1 | 2 | P6-17 holderType 单复数、P6-01 审批副作用 |
| 7 Query/Importer | 0 | 1 | 1 | 4 | P7-14 PathData 导入缺 canWrite |
| 8 横切/其他 | 0 | 1 | 2 | 6 | P8-11 notification 永久空 |
| **合计** | **2** | **13** | **16** | **22** | 共 53 项 |

> 第3轮重构成效显著：**第2轮 6 CRITICAL + 29 HIGH 中绝大多数已闭环**（域4 全部 14 项、域6 P6-02/03/04/06/07/09、域2 P2-01~10、域3 P3-01/02/03、域5 P5-01/02 等）。本轮 2 个新 CRITICAL 均为**第2/3轮未覆盖的写入路径**（PathData 创建、基线链接创建）。

---

## 二、2 个 CRITICAL（主 agent 已用 psql 直接核实，均可直接修复）

| # | 编号 | 问题 | 文件:行号 | 症状 | 修复 |
|---|------|------|-----------|------|------|
| C1 | **P2-14** | PathData 关联表 INSERT 列名错 | `services/products/path_data_service.py:316-323` | INSERT 用 `iteration`，实际列名 `prdinstanceiteration_iteration`（psql `\d` 确认）→ 所有创建/编辑 PathData 写关联表时 `column "iteration" does not exist` → 500 | `iteration` → `prdinstanceiteration_iteration` |
| C2 | **P3-11** | 基线 substituteLinks/optionalUsageLinks 写错表 + str 当 dict | `services/product_structure.py:947-964`（create_baseline）| 对路径字符串调 `.get()` → AttributeError 500；且写 `partsubstitutelink`/`UPDATE partusagelink` 而非 `productbaseline_substitutelink.substitutelinks`（psql `\d` 确认）→ 传非空链接创建基线必 500，语义全错 | 改 INSERT `productbaseline_substitutelink`/`productbaseline_optionallink` 路径字符串 |

> 两者均仅在有对应数据/非空入参时暴露（清单#18），空库/GD50 当前无 PathData 与含替代链接的基线，故前两轮及机器脚本未触发。**修复后须 GD50 造数据复测 + pytest 282 基线。**

---

## 三、13 个 HIGH

### 权限 / 安全（系统性缺口——第3轮重构遗漏 + 新暴露，最紧要）
- **P1-13** `remove_tag` 完全无 ACL 写权限检查（add_tag/set_tags 有）→ 任意成员删任意零件标签
- **P4-NEW1** `mark_obsolete` 缺写权限检查（Java 首行 checkDocumentRevisionWriteAccess）
- **P4-NEW2** 文档 `set_tags/add_tag/remove_tag` 三方法均缺写权限检查
- **P5-19** 用户组/成员 7 个写端点缺 admin 校验（create_group/delete_group/enable-group/disable-group/group-access/add-user/remove-from-workspace）
- **P5-07-REG** admin stats + index 8 个端点缺 admin 校验（第2轮 P5-07 只修了 2 个，同类其余回归）
- **P7-14** `import_into_path_data` 缺实例级 canWrite（Java productInstanceManager.canWrite）

> **共性根因**：标签/obsolete/用户组/stats 这些"非核心 CRUD"端点在第3轮统一 Depends/迁移 service 时被系统性遗漏权限检查。建议作为一个专项批次统一修复。

### 功能错误 / 返回错数据
- **P2-15**（=域1 P1-14）product_manager 服务层 2 处硬编码 HTTPException（`:1895/:2007`，Phase0 命中）
- **P2-06** `_resolve_pi_config_spec` 缺 configurationitem_id 过滤 → 同 serial 跨 CI 取错迭代
- **P5-18** setUserAccess 用 UPSERT，非成员用户触发 FK 500（应 400）
- **P6-17** holderType 单复数不一致（`"part"` vs Java `"parts"`、`"workspace-workflow"` vs `"workspace-workflows"`）→ 前端任务路由错
- **P6-01** process_task 缺审批后 release/通知副作用（核心状态机已对齐；通知属邮件族排期）
- **P8-11** notification `list_for_user` 用 `ackauthor_login==login` 过滤未读，未读通知该列为 NULL → 恒返回空（psql 确认 10 条未读全 NULL）

---

## 四、修复优先级建议

### ① 可直接修复（低风险、明确）— 建议立即
1. **P2-14**（改 1 列名）、**P3-11**（改写入表）— 2 个 CRITICAL，一行/一段级修复
2. **P8-11**（移除 ackauthor_login 过滤条件）
3. **P6-17**（holderType 统一复数，全局替换约 12 处）
4. **P5-18**（UPSERT 改 SELECT-then-UPDATE）
5. 权限专项批次：**P1-13 / P4-NEW1 / P4-NEW2 / P5-19 / P5-07-REG / P7-14**（统一补 check_write_access / require_(workspace_)admin / canWrite）
6. **P2-15/P1-14**（硬编码 HTTPException → 领域异常）、**P8-12**（products.py 路由异常）

### ② 需评估后修复（涉行为/事务语义）
- **P2-06/P2-16**（configSpec 缺 CI 过滤 + 未按基线 collection 完整解析）
- **P7-15**（import checkout/checkin 事务边界，需改 service commit 语义）
- **P3-03**（put_effectivity 强制下限字段，可能影响前端调用）
- **P1-12**（create_new_version 描述写错版本 + 忽略 workflowModel/acl/roleMapping）

### ③ 已知计划外项（不在本轮修复范围）
- **P6-01/P6-08** 审批通知邮件 — 邮件通知族全量迁移已排期（loose-ends 第八节，用户选 B 对齐 NotifierBean）
- **P5-12** put_index ES 桩、**P5-21** delete_account 级联不全（replica 模式绕过 FK）

### MED/LOW（16 MED + 22 LOW）
状态码不一致（P2-12/P5-16 应 204、P8-03/P8-09/P8-10 响应形态）、DTO 多/少字段（P5-08/P5-20/P8-08）、死代码（P3-12）、幂等（P7-12）、桩（P4-NEW4/P8-06 lov_deletable 检查不全）等——收尾批次统一处理。

---

## 五、本轮相对前两轮的差异标注

### 已闭环（第3轮重构修复，本轮确认）
- 域4 Documents：**14 项全部闭环**（含 P4-01 CRITICAL attachedFiles）
- 域6：P6-02/P6-03（2 CRITICAL）、P6-04/06/07/09/10/12/13
- 域2：P2-01/02/03/04/05/07/09/10（含 P2-02 search_ci 500）
- 域3：P3-01/02/03（3 HIGH）+ P3-04/05/06/08
- 域5：P5-01/02（2 CRITICAL）+ P5-03/05/06/09/10/11/13
- 域7：P7-01/04/08/10 + P7-03 子问题 A
- 域8：P8-01/02/04/05

### 新增（本轮新发现，前两轮未覆盖）
- 2 CRITICAL（P2-14 PathData INSERT、P3-11 基线链接写入）— 均写入路径盲区
- 权限系统性缺口（P1-13/P4-NEW1/P4-NEW2/P5-19/P7-14）
- P6-17 holderType、P8-11 notification、P8-12 products 异常

### 回归 / 修复引入副作用（第3轮重构隐患，须重点关注）
- **P5-18**：第2轮 P5-04 修 membership 校验时引入 UPSERT → 新 500 面
- **P5-07-REG**：P5-07 只修 2 端点，同类 8 个 stats/index 端点未覆盖（部分回归）
- **P2-15/P1-14**：第3轮把 router 逻辑迁进 service 时带入硬编码 HTTPException
- **P2-06**：configSpec 从"降级 latest"改进为"基线解析"时漏 configurationitem_id 过滤

### 证伪 / 澄清（延续第2轮结论）
- P6-05（Java WorkflowModel 也无 reference）、P7-02（Java BomImporter 0 实现，死代码）

---

## 六、机器脚本结果（阶段0，均已人工甄别）
| 脚本 | 结果 | 甄别 |
|------|------|------|
| `validate_sql_columns` | 1 error + 12 warning | 全部误报：`id` 自增列 NOT-NULL 缺失、`ON CONFLICT DO UPDATE SET` 被当表名 |
| `validate_dto_fields` | 2 "CRITICAL" | 全部误报：CreationDTO 误映射到响应 DTO（PathDataIterationCreationDTO/ProductBaselineCreationDTO） |
| `check_hardcoded_exceptions` | **2 真问题** | product_manager.py:1895/2007 → P2-15/P1-14（HIGH/MED） |
| `audit_write_stubs` | roles DELETE / workflow-models / add-user "STUB" | 全部第2轮已确认假报（脚本删后对比误判）；脚本自身 tags 断言崩溃 |
| pytest 基线 | **282 passed, 1 skipped** | 全绿，无回归基线 |

---

## 七、验证方法（供修复轮次使用）
- pytest 基线：`docdoku-plm-server-py/` 下 `venv/bin/python -m pytest -q` → 282 passed, 1 skipped
- Payara 对拍：FastAPI `:8009` vs front(Payara) `:8005`，同请求对比 JSON
- DB 真值：`docker exec docdoku-plm-docker-db-1 psql -U changeit -d docdokuplm -c "\d 表名"`
- CRITICAL 复测：P2-14 需造 PathData、P3-11 需造含 substituteLinks 的基线创建请求（清单#18：空库测不到）
