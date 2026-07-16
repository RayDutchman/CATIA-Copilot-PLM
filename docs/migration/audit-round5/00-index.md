# 迁移代码第5轮全量审计 总报告 — 00 Index

> 生成日期：2026-07-15 ｜ 范围：`docdoku-plm-server-py` 全量迁移代码 vs Java/Payara **逐端点/逐SQL/逐DTO全覆盖**
> 方法：主 agent 跑机器脚本 + Payara 对拍收集线索（阶段0）→ 8 域 explore subagent 逐条 SQL + 逐 DTO 字段独立验证（阶段1 两波）→ 主 agent 汇总去重定级（阶段2）
> 基准 workspace = GD50（种子数据）｜ **纯审计，不做修复**
> ⚠️ 本轮**只审计不修复**；LOW 不修、邮件族不迁移（用户确认"只做全量审计"）

## 一、问题总计

| 域 | CRITICAL | HIGH | MED | LOW | 说明 |
|----|:---:|:---:|:---:|:---:|----|
| 1 Parts | 0 | 1 | 5 | 4 | P1-15 search_parts 日期过滤字段错（HIGH） |
| 2 Products | 0 | 0 | 1 | 4 | 域2非常干净，仅 P2-08(MED)保留+P2-17~20(LOW) |
| 3 Baselines/Effectivity | 0 | 1 | 3 | 3 | P3-14 BaselinedPartDTO字段名number≠partNumber（HIGH） |
| 4 Documents | 0 | 0 | 2 | 2 | P4-NEW5/6 权限缺口（MED） |
| 5 Workspace/用户/权限 | **1** | 2 | 0 | 1 | P5-NEW-01方法体丢失CRITICAL；权限+DTO回归 |
| 6 Workflow/Change/Tasks | **1** | 1 | 0 | 2 | P6-19 CRITICAL ChangeRequest删除列名错；P6-20 DTO导入错→500 |
| 7 Query/Importer | 0 | 0 | 1 | 1 | P7-15-REG Phase2事务回归（MED） |
| 8 横切/其他 | 0 | 0 | 0 | 6 | 全部为前轮保留LOW，无新发现 |
| **合计** | **3** | **5** | **12** | **23** | 共 43 项（含前轮遗留LOW） |

---

## 二、3 个 CRITICAL（本轮新发现，前四轮均未暴露）

| # | 编号 | 域 | 问题 | 文件:行 | 症状 |
|---|------|---|------|----------|------|
| C1 | **P5-NEW-01** | 5 | `get_workspace_front_options` 方法体丢失 | `services/workspace_manager.py:333-348` | `def` 行缺失，方法体缩进到前一方法内成为死代码 → `GET /workspaces/GD50/front-options` → 500（`AttributeError: no attribute`） |
| C2 | **P6-19** | 6 | `delete_item()` ChangeRequest affected 清理用错列名 | `services/change_manager.py:251-262` | `DELETE FROM changereq_affected_part WHERE changereq_id=...` → 列名实际为 `changerequest_id`（`\d` 确认）→ **删除 ChangeRequest 完全不可用，必 500** |
| C3 | P1-15 | 1 | `search_parts` 修改时间过滤用 `check_out_date` 而非 `modification_date` | `services/product_manager.py:1354-1361` | 搜索结果不准确（签出久但刚改的搜不到）→ 应归入 HIGH，主 agent 定级 HIGH（语义偏差，非 500） |

**修正**：P1-15 是**功能错误**（非500崩溃），主 agent 复定级为 **HIGH**。实际 C1=C2=2 个 CRITICAL。

> C1/C2 的共同特征：**代码存在但逻辑不可达**（方法体缩进错/列名映射错），两处均 500 崩溃。机器脚本和 pytest 均未覆盖这些写入/配置读取路径（清单#18）。

---

## 三、5 个 HIGH

| # | 域 | 编号 | 问题 | 影响 |
|---|-----|------|------|------|
| H1 | 1 | P1-15 | search_parts 时间过滤字段错（check_out_date vs modification_date） | 零件搜索功能返回错误结果集 |
| H2 | 3 | **P3-14** | BaselinedPartDTO 字段名 `partNumber` → Java 用 `number`；缺 `name` 字段 | 前端取 `undefined` — 基线零件列表功能受损 |
| H3 | 5 | P5-NEW-02 | `workspace_memberships._workspace_to_dict` 仍含 `admin` 字段 → extra=forbid 500 | remove_user/set_admin 端点 500 |
| H4 | 5 | P5-NEW-03 | `remove_from_group` 缺 admin 权限检查 | 任何成员可移除组成员 |
| H5 | 6 | **P6-20** | GET workspace-workflows/{id} 导入错误的 WorkspaceWorkflowDTO（misc版 vs ws版）→ 500 | 端点运行时必 500 |

---

## 四、12 个 MED

| 域 | 编号 | 问题 |
|----|------|------|
| 1 | P1-16 | workflow 字段始终返回 None（PartRevisionDTO） |
| 1 | P1-17 | PartTemplate 缺少 DELETE/PUT 文件端点 |
| 1 | P1-18 | 模板 CRUD 端点缺 workspace write-access 检查 |
| 1 | P1-19 | get_conversion_status 返回 204 vs Java 200+null |
| 1 | P1-20 | _next_version 多字符版本递增跳步（AZ→AZA 而非 BA） |
| 2 | P2-08 | linkType 过滤仅最小实现（前轮保留） |
| 3 | P3-15 | baseline GET/DELETE 缺 workspace 归属校验（水平越权） |
| 3 | P3-16 | document_baseline delete 缺 workspace 归属校验 |
| 3 | P3-17 | effectivity CI ID 从扁平字段读取 vs Java 从嵌套对象 key.id |
| 4 | P4-NEW5 | create_new_version 缺写权限检查 |
| 4 | P4-NEW6 | rename_put 缺 workspace 写权限 |
| 7 | P7-15-REG | import_into_path_data Phase2 各路径独立 commit，非原子 |

---

## 五、第4轮问题闭环确认

**本轮独立验证了第4轮全部 CRITICAL/HIGH/MED 修复项，逐条重定位代码确认已闭环**：

| 域 | 闭环项 | 关键验证 |
|----|--------|---------|
| 1 | P1-13(remove_tag权限)/P1-12(description)/P2-15(异常) | 代码行号重新定位，确认已修 |
| 2 | P2-14(CRITICAL列名)/P2-06(configSpec)/P2-12(204)/P2-16 | 全部重新验证 |
| 3 | P3-11(CRITICAL基线链路)/P3-10(decode_path)/P3-03(强制下限)/P3-12(死代码)/P3-09(FK守卫) | 全部重新验证 |
| 4 | P4-01~14 全部 14 项 + P4-NEW1/2/3/4 | 全部重新验证 |
| 5 | P5-18(UPSERT)/P5-19(用户组)/P5-07-REG(admin)/P5-08(schema)/P5-16(204)/P5-20(membership) | 全部重新验证；**发现 P5-NEW-02 回归** |
| 6 | P6-02/03(CRITICAL)/P6-04/06/07/09/17(HIGH)/P6-18(MED) | 全部重新验证 |
| 7 | P7-14(canWrite)/P7-15(auto_commit)/P7-04/08/10/12 | 全部重新验证；**发现 P7-15-REG 回归** |
| 8 | P8-01/02/04/05/06/11/12 | 全部重新验证 |

**第4轮修复总体稳固，但发现 2 处回归**：
- **P5-NEW-02**：P5-08 只删了 `workspaces.py` 和 `admin.py` 的 `admin` 字段，但在 `workspace_memberships.py` 的 `_workspace_to_dict` 中遗留，导致 remove_user/set_admin 端点 500
- **P7-15-REG**：P7-15 给 `import_into_parts` 加了 `auto_commit=False` 事务模型，但 `import_into_path_data`（Phase2）未同步改造，各路径仍独立 commit

---

## 六、机器脚本与 Payara 对拍结果

| 工具 | 状态 | 线索 |
|------|------|------|
| `validate_sql_columns` | 1 误报（ON CONFLICT DO UPDATE SET） | 无真问题 |
| `check_hardcoded_exceptions` | ✅ 干净（0处） | 第4轮修复后已清零 |
| `validate_dto_fields` | 2 假 CRITICAL（CreationDTO 误映射） | 已知误报 |
| `audit_write_stubs` | 3 假 STUB + 脚本自身 crash | 已知误报 |
| `endpoint_behavior_test` | 10/10 通过 | 基线 CRUD + 404 + 401 一致性验证 |
| `compare_all_endpoints` | MATCH:80 / PARTIAL:45 / MISMATCH:33 | 多数 MISMATCH 经独立验证为脚本认证/参数问题（手工 curl 返回正常），需分域验证 |
| pytest 基线 | **282 passed / 1 skipped** | 零回归 |

---

## 七、与第4轮审计差异

| 维度 | 第4轮 | 第5轮 |
|------|------|------|
| 审计深度 | 规则驱动（22条要点） | **逐行覆盖**：每条裸SQL对`\d`验证、每个DTO逐字段对照Java |
| SQL覆盖 | 重点表抽查 | **全部裸SQL**逐条填入核验表 |
| DTO覆盖 | 重点DTO差异核对 | **全部DTO**逐字段填入对照表 |
| 输出粒度 | 问题列表 | 问题列表 + SQL核验表 + DTO对照表 |
| LOW覆盖 | 不列入（22 LOW淘汰） | **全部记录**，标注与第4轮关系 |
| 新发现 | 主要聚焦第3轮重构回归 | 聚焦代码完整度（写入路径、事务回归、DTO字段名错误） |

---

## 八、审计产出

| 文件 | 路径 |
|------|------|
| 本总报告 | `docs/migration/audit-round5/00-index.md` |
| 域1 Parts | `docs/migration/audit-round5/01-parts.md` |
| 域2 Products | `docs/migration/audit-round5/02-products.md` |
| 域3 Baselines | `docs/migration/audit-round5/03-baselines-effectivity.md` |
| 域4 Documents | `docs/migration/audit-round5/04-documents.md` |
| 域5 Workspace/用户/权限 | `docs/migration/audit-round5/05-workspace.md` |
| 域6 Workflow/Change/Tasks | `docs/migration/audit-round5/06-workflow-change-tasks.md` |
| 域7 Query/Importer | `docs/migration/audit-round5/07-query-importer.md` |
| 域8 横切/其他 | `docs/migration/audit-round5/08-crosscutting.md` |
