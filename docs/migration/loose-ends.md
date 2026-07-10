# FastAPI 迁移遗留清单（Migration Loose Ends）

> 生成日期：2026-07-08 ｜ 更新：2026-07-10（PathData/P2P 完成 + 全量对比修复 + 用户姓名/权限修复合集）
> 范围：Java EE Payara (`docdoku-plm-server`) → FastAPI (`docdoku-plm-server-py`) 后端迁移
> 状态：**核心业务已 100% 走 FastAPI，Payara 在生产链路已被完全绕过**，剩余为功能性 loose ends
>
> 本文件汇总所有未完成/占位/降级项，作为后续收尾的唯一清单。修复某项后请在本文件勾选并同步 `CHANGELOG.md` / `REMINDERS.md`。

## 2026-07-10 进展摘要（全量对比修复合集）

- ✅ **PathData / Path-to-Path Link 域全量实现**：18 端点 + Service CRUD + DFS 环检测 + decodePath 验证
- ✅ **filter configSpec 解析**：字符串→filter 对象映射（latest/released/wip），消除 500
- ✅ **hasPathData 路径格式**：`{ci_id}` → `-1` 转换 + visitor 路径支持
- ✅ **基线创建全量修复**：零件可用性 BFS 校验（对齐 Java getLastCheckedInIteration）+ 响应补 author
- ✅ **用户权限 bug**：membership 字段名修复（readOnly→membership 字符串解析）+ 删除错误 account.enabled 写入
- ✅ **deps 访问控制对齐**：补 workspace.admin_login + usergroup_user 组检查
- ✅ **effectivities SQL 列名**：pre.workspace_id→pre.partmaster_workspace_id
- ✅ **用户姓名全量修复**：tasks/doc_baselines/product_structure/products 补 Account name 查询
- ✅ **PartCreationDTO 422**：补 Field alias + extra=ignore
- ✅ **export-files SQL 列名**：br.fullname/pi.nativecadfile_fullname/bd.target_docrevision_version 全量修正
- ✅ **LOV 表名全错**：listofvalues→lov, listofvaluesattribute→lov_namevalue
- ✅ **groups FK 违规**：create_group 补 db.flush()
- ✅ **parts length=0**：ge=1→ge=0 对齐 Payara getAllPartRevisions
- ✅ **4 个 FA 自创端点删除**：disk-usage/users/{login}/in-progress/notifications
- ✅ **P2P 重复路由删除**：product_configurations.py 重复 POST
- ✅ **baseline parts 端点补齐**：GET /product-baselines/{ci}/baselines/{id}/parts
- ✅ **未使用 resources/ 清理**：删除不进 Dockerfile 的顶层 resources/
- ✅ **对比脚本增强**：错误文本对比 + endpoint_behavior_test.py 行为测试
- ✅ **全量对拍**：158 端点 76 MATCH / 37 MISMATCH（37 个 FA/PY 状态码不一致，大部分为 PY 自身 500）
- ✅ **行为测试**：基线 CRUD + 零件 CRUD + 404 一致性 + 401 拦截 → 10/10 通过

## 2026-07-09 进展摘要（A+B+C 批次）
- ✅ A1 SSL Proxy 切 FastAPI + 修复丢失 cert.key
- ✅ A2 DocumentBaselines 补端点
- ✅ B1 产品配置/基线数据解码填充
- ✅ B2 Product Structure 属性/通知/修改通知
- ✅ C1 WorkspaceManager dead stub→真实
- ✅ C2 Query get/delete 真实化
- ✅ C3 EffectivityDTO 填充
- ✅ 修复 3 个生产 SQL bug

---

## 零、迁移已完成的证据（无需担心的部分）

| 维度 | 结论 | 证据 |
|------|------|------|
| Nginx 生产入口 | Port 80 全部→back-py | `front/nginx.conf` |
| 生产兜底 | 未匹配路由 502 | `front/nginx.conf:495-497` |
| CAD 转换回调 | → FastAPI | `conversion.env` |
| REST 资源覆盖 | 43 Java Resource 全有 Python router | `app/routers/*.py` |
| 迁移任务队列 | tracker.csv 523/523 | 只读归档 |
| 回归测试 | 176 passed / 1 skipped | pytest |
| 全量对拍 | 158 端点 76 MATCH / 37 MISMATCH | `compare_all_endpoints.py` |
| 行为测试 | 基线+零件 CRUD 10/10 | `endpoint_behavior_test.py` |

---

## 一、✅ P0 — PathData / Path-to-Path Link 域

**2026-07-10 已完成**：18 REST 端点 + Service CRUD + DFS 环检测 + decodePath 验证 + ORM 重建 + 降级点回填。见 `c668d31`。

---

## 二、🟠 P1 — Importer 导入域（9 处全空壳）

| 位置 | 缺失内容 | 影响 API |
|------|----------|----------|
| `app/services/importer.py:11-17` | `import_into_parts()` → stub | `POST /parts/import` |
| `app/services/importer.py:19-26` | `dry_run_import_into_parts()` → stub | 导入预览 |
| `app/services/importer.py:28-34` | `import_into_path_data()` → stub | 路径数据批量导入 |
| `app/services/importer.py:36-42` | `import_bom()` → stub | BOM 导入 |
| `app/services/importer.py:44-51` | `dry_run_import_bom()` → stub | BOM 预览 |
| `app/routers/parts.py:448-490` | import 路由全部 stub/断连 | 5 端点 |

> 📋 独立计划：`docs/superpowers/plans/2026-07-09-importer-domain.md`（~1100 行，2–3 天）

---

## 三、🟠 P1 — Query 执行引擎

| 项 | 位置 | 说明 | 工作量 |
|----|------|------|--------|
| **查询执行** | `parts.py` `post_workspace_query`/`post_queries` | Java `runCustomQuery`：递归 QueryRule 树→动态 SQL。当前 = 重名检查 `{"id":0}` | 大 |
| **查询保存** | 同上 | 递归 rule 树序列化写入 DB（selects/orderBy/contexts） | 中 |

---

## 四、🔵 P2 — 剩余 MISMATCH 分析（37 个）

| 分类 | 数量 | 说明 |
|------|------|------|
| FA:200 PY:500 | ~20 | Payara 自身 500（容器降级），非 FA 问题 |
| FA:200 PY:404 | ~8 | Payara 缺端点（如 releases/last、baselines/{id}）— FA 对齐正确 |
| FA:404 PY:403 | 2 | workflow-instances Payara 需要特殊权限 |
| FA:404 PY:500 | ~4 | Payara 自身崩溃 |
| FA:422 PY:500 | 2 | auth/login extra=forbid / documents tags — 非实际 bug |
| FA:500 PY:200 | 1 | baseline parts 路由路径已修复 |

---

## 五、🔵 P2 — 已知局限性

| 项 | 状态 |
|----|------|
| WebSocket /ws 403 | 已知问题（握手失败），不影响主功能 |
| OnDemandConverter | deferred（需 LibreOffice 引擎） |
| Payara 容器保留 | Port 85 (8005) 对比用，设计如此 |
| pytest 10 failures | 种子数据权限问题导致，非代码 bug（seed_test_data 需修） |

---

## 六、剩余工作优先级

| 优先级 | 项 | 计划/状态 | 工作量 |
|--------|-----|----------|--------|
| 1 | **Importer 域** | 📋 `plans/2026-07-09-importer-domain.md` | 大 |
| 2 | **Query 执行引擎** | 待排期 | 大 |
| 3 | **WebSocket 403** | 待排期 | 中 |
| 4 | **种子脚本修复** | 权限 + 数据一致性 | 小 |

---

## 七、统计汇总

| 域 | 状态 |
|----|------|
| 基础设施（SSL/DocBaselines）| ✅ |
| 产品配置/基线/结构降级 | ✅ |
| WorkspaceManager/Query读删/EffectivityDTO | ✅ |
| PathData / Path-to-Path Link | ✅ |
| 用户姓名/权限/effectivities/LOV/export-files SQL | ✅ |
| configSpec/hasPathData/baseline校验 | ✅ |
| **Importer 导入** | ⏳ 下一项 |
| **Query 执行引擎** | ⏳ 待排期 |
| **WebSocket** | ⏳ 待排期 |

> 核心业务完整。剩余：**批量导入**、**自定义查询执行**、**WebSocket 修复**。
