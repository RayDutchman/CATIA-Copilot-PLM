# 迁移收尾 A+B+C 实施计划（2026-07-09）

> **For agentic workers:** 本计划执行 FastAPI 迁移剩余的中小工作量项（A 基础设施 / B 数据降级 / C 小 stub）。PathData 与 Importer 两大域另有独立计划。步骤用 checkbox 跟踪。

**Goal:** 今日完成 `migration/loose-ends.md` 中除 PathData(第一节) 与 Importer(第二节) 外的所有 loose ends（~25 项），全部对齐 Payara，回归测试不退化并部署。

**Architecture:** 纯 FastAPI 代码修改 + 一处 nginx 配置。部署走 `docker cp` + `docker restart back-py`（build 不可用）。SSL proxy 改为以 `front` 为单一路由权威。

**Tech Stack:** FastAPI, SQLAlchemy(raw SQL 为主), Pydantic v2, nginx。

## Global Constraints（铁律）
- **对齐 Payara**：所有字段名/类型/DTO 结构以 `docdoku-plm-server/.../rest/dto/*.java` 与 `*Resource.java` 为准，不自创。
- **不能 rebuild**：容器改动用 `docker cp` + `docker restart docdoku-plm-docker-back-py-1`。
- **extra=forbid 风险**：新增/修改 helper 返回 dict 前，逐字段核对 response schema。
- **测试基线**：pytest 176 passed / 1 skipped，任何改动不得退化。
- **不自动 commit**（等用户指示）。
- 参考 Java↔Python 映射：`docs/migration/tracker.csv`。

---

## 批次 A — 基础设施（高价值低风险）

### Task A1 — SSL Proxy(9000→443) 切 FastAPI
- 文件：`docdoku-plm-docker/proxy/nginx.conf`
- 方案：将 `location /docdoku-plm-server-rest/api` 和 `/ws` 的 upstream 从 `back:8080` 改为 `front`（让 front 成为唯一路由权威，复用其 FastAPI 全覆盖 + 502 兜底 + ws upgrade）。
- [ ] 改 api location upstream → `front`
- [ ] 改 ws location upstream → `front`（保留 upgrade 头）
- [ ] `docker cp proxy/nginx.conf` 到 ssl-proxy 容器 + `nginx -s reload`
- [ ] 验证：`curl -k https://localhost:9000/docdoku-plm-server-rest/api/platform/health`

### Task A2 — DocumentBaselines 补 3 端点
- 文件：`app/routers/document_baselines.py`；参考 Java `DocumentBaselinesResource.java` + `DocumentBaselineDTO`
- 缺：`GET /{id}`（详情）、`GET /{id}-light`（轻量）、`GET /{id}/export-files`
- [ ] 读 Java resource 确认 3 端点签名 + DTO 字段
- [ ] 读现有 document_baselines.py + service 层
- [ ] 实现 3 端点（对齐 DTO）
- [ ] pytest + 冒烟

---

## 批次 B — 数据降级修复（复用已有查询）

### Task B1 — 产品配置/基线 substitutesParts/optionalsParts
- 文件：`app/routers/product_configurations.py`(73-76,107-111,126-130)、`app/routers/product_baselines.py`(58-59,79-80)
- 参考：baseline 已有 `_query_substitute_links`/`_query_optional_links` 可复用；对齐 Java `ProductBaselineDTO.substitutesParts/optionalsParts`（`List<LightPartLinkListDTO>`）
- [ ] 读 Java DTO 确认 substitutesParts/optionalsParts 结构
- [ ] 实现查询 helper（substitutes/optionals parts）
- [ ] 填充 product_configurations 四字段 + baselines 两字段
- [ ] pytest + 冒烟

### Task B2 — Product Structure attributes/notifications
- 文件：`app/services/product_structure.py`(163,165,168,256,258)、`app/routers/products.py`(65)
- [ ] `_build_component`/`_convert_visitor_component` 查实例属性填 `attributes`
- [ ] 填 `notifications`（修改通知查询）
- [ ] `_ci_to_dict` 的 `hasModificationNotification` 真实查询
- [ ] pytest + 冒烟

---

## 批次 C — 小型单表 stub

### Task C1 — WorkspaceManager 5 stub
- 文件：`app/services/workspace_manager.py`(88-109)
- [ ] `get_disk_usage()` → 基于 vault/DB binaryresource 求和
- [ ] front/back options 读写 `workspacefrontoptions`/`workspacebackoptions` 表（4 方法）
- [ ] 确认对应 router 端点接线正确
- [ ] pytest

### Task C2 — Query CRUD 4 stub
- 文件：`app/routers/parts.py`(250-308)；参考 Java `PartsResource` query 端点 + `QueryDTO`
- [ ] `get_queries` 真实查库
- [ ] `post_workspace_query`/`post_queries` 真实创建
- [ ] `delete_query` 真实删除
- [ ] pytest

### Task C3 — OnDemandConverter 2 + EffectivityDTO 1
- 文件：`app/services/ondemand_converter.py`(11-23)、`app/schemas/misc/effectivity.py`
- [ ] OnDemandConverter：评估可行性（依赖转换引擎）；若不可行则明确降级注释并留 loose-end（对齐 Payara 行为：无引擎时的返回）
- [ ] EffectivityDTO：按 Java `EffectivityDTO` 填字段（当前空壳仅 `pass`）
- [ ] pytest

---

## 收尾
- [ ] 全量 pytest（≥176 passed）
- [ ] `venv/bin/python -c "import app.main"` 通过
- [ ] docker cp 所有改动文件 + restart back-py + health ok
- [ ] 线上冒烟：逐 batch 关键端点 200/204 无 500
- [ ] 更新 `migration/loose-ends.md`（勾选已完成项）、`CHANGELOG.md`、`REMINDERS.md`
- [ ] 写 PathData 域详细计划 `docs/superpowers/plans/2026-07-XX-pathdata-domain.md`
- [ ] 写 Importer 域详细计划 `docs/superpowers/plans/2026-07-XX-importer-domain.md`
- [ ] 不自动 commit

---

## 两大域另行排期（今日只出计划）
- **PathData/Path-to-Path**：15–20h。拦路虎：复合主键 ORM 重建、环检测算法、rebase 级联文件拷贝、文件存储层。18 端点 + ~15 service 方法。
- **Importer**：2–3 天。拦路虎：openpyxl 需 docker cp wheel 手动装、.xls→.xlsx 格式、~1100 行（cell-comment 元数据解析）、BOM 导入 Java 无实现。
