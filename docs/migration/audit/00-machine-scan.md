# 阶段 0：机器扫描基线

> 生成：2026-07-11 ｜ 审计工具：`docdoku-plm-server-py/scripts/*`
> 用途：为 8 个域 subagent 提供机器可检测的问题线索基线。**所有条目需 subagent 人工代码对比复核**（脚本有已知误报）。

## 环境说明（影响运行时类审计）

- **Workspace_2 已被删除**（用户确认）。当前 DB 唯一有数据的 workspace = `GD50`（31 partmaster、1 configurationitem、0 documentmaster）。
- 依赖 Workspace_2 的运行时脚本（`audit_write_stubs.py`、`compare_all_endpoints.py`、`endpoint_behavior_test.py`）与 pytest 大量失败，**均为环境数据问题，非代码回归**。
- 本次审计聚焦**代码对比**（Java 源 vs Python 迁移代码），运行时/测试类问题延后处理。

## Java 源码根路径（subagent 对照用）

| 层 | 根路径（相对 `docdoku-plm-server/`）|
|----|----|
| REST Resource | `docdoku-plm-server-rest/src/main/java/com/docdoku/plm/server/rest/` |
| REST DTO | `docdoku-plm-server-rest/src/main/java/com/docdoku/plm/server/rest/dto/` |
| EJB Service Bean | `docdoku-plm-server-ejb/src/main/java/com/docdoku/plm/server/` |
| Core 领域模型 | `docdoku-plm-server-core/src/main/java/com/docdoku/plm/server/core/` |

Python 迁移代码根：`docdoku-plm-server-py/app/`（`routers/` `services/` `schemas/` `models/` `core/` `ws/` `ext/`）

## 1. check_hardcoded_exceptions.py

结果：✅ **`app/services/` 下未发现硬编码 HTTPException**（干净）。
注意：脚本只扫 `services/`，**routers/ 层的硬编码桩不覆盖**，subagent 需自行 grep routers。

## 2. validate_sql_columns.py（3 error + 14 warning）

- ❌ `UPDATE SET → 表不存在` ×3：`user_groups.py` / `users.py` / `workspace_memberships.py`
  → **疑似解析器误报**（多表 UPDATE 或别名），subagent 须核对实际 SQL 表名对 `information_schema`。
- ⚠️ `INSERT 缺 NOT NULL 列 ['id']` ×14：document_baselines/documentcollection、documentlink、oauthprovider、instanceattribute、partcollection、pathdatamaster、pathtopathlink、workflow、webhook/webhookapp 等
  → 多为 **SERIAL/自增 id 误报**，但 `instanceattribute` 缺列须重点核（清单要点 5：dtype 判别列）。

## 3. validate_dto_fields.py（2 CRITICAL + 27 WARNING）

- 🔴 CRITICAL ×2：`PathDataIterationCreationDTO`、`ProductBaselineCreationDTO`
  → **已知误报**：脚本把 CreationDTO 错配到响应 DTO（清单要点 2 明确记载）。仍需 subagent 确认 Creation 与响应 DTO 各自字段。
- 🟡 WARNING ×27：多为 CreationDTO/响应 DTO 配对偏差，subagent 按域逐个核对 alias/类型/extra 策略。

## 4. 运行时脚本（本轮延后）

- `audit_write_stubs.py`：13 端点因无 Workspace_2 → 12 SKIP / 1 PERSIST。延后。
- `compare_all_endpoints.py` / `endpoint_behavior_test.py`：硬编码 Workspace_2。延后。
- GD50 核心读端点手工对拍（FA:8009 vs Payara:8005）：24/25 MATCH，唯一 MISMATCH = `GET /parts/tags` FA=400 PY=404（待波1 Parts 域复核）。

## pytest 基线（延后，仅记录）

- 84 failed / 183 passed / 7 skipped / 6 error（`test_vault.py` 收集错误：`vault.py` 缺 `part_geometry_path`）。
- 绝大多数为 Workspace_2 缺失导致的 404 连锁，非回归。`test_vault.py` 导入错误是真实符号缺失线索，交横切域。
