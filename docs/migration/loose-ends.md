# FastAPI 迁移遗留清单（Migration Loose Ends）

> 生成日期：2026-07-08 ｜ 更新：2026-07-09（A+B+C 批次完成）
> 范围：Java EE Payara (`docdoku-plm-server`) → FastAPI (`docdoku-plm-server-py`) 后端迁移
> 状态：**核心业务已 100% 走 FastAPI，Payara 在生产链路已被完全绕过**，剩余为功能性 loose ends
>
> 本文件汇总所有未完成/占位/降级项，作为后续收尾的唯一清单。修复某项后请在本文件勾选并同步 `CHANGELOG.md` / `REMINDERS.md`。

## 2026-07-09 进展摘要（A+B+C 批次）
- ✅ **A1 SSL Proxy(9000→443) 切 FastAPI**：`proxy/nginx.conf` API+ws 改指向 `front`（复用 FastAPI 全覆盖）。附带修复丢失的 `cert.key`（自签名重建，crash-loop 1117 次已止）。
- ✅ **A2 DocumentBaselines**：补 `GET /{id}` + `GET /{id}-light`（export-files 早已存在）；修复 `type` int→enum 名 latent 500。
- ✅ **B1 产品配置/基线 substitutesParts/optionalsParts**：用 decode_path 从 link 路径表解码填充；config substituteLinks schema 改 `List[str]` 对齐 Payara。
- ✅ **B2 Product Structure**：`attributes`（实例属性）/`notifications`/`hasModificationNotification` 全量遍历路径已真实查询。
- ✅ **C1 WorkspaceManager**：5 个 dead stub 改为真实实现；`/disk-usage` 返回真实 vault 总量。
- ✅ **C2 Query**：`get_queries`（递归 rule 树）/`delete_query`（级联删）真实化。POST=查询执行引擎（recursive rule + 执行），改列为**新 loose-end**（见下）。
- ✅ **C3**：OnDemandConverter 注释明确化（需 LibreOffice 引擎，deferred）；EffectivityDTO 空壳→填充字段。
- ✅ **附带修复 3 个 pre-existing 生产 SQL bug**（Workspace_2 有基线数据才暴露）：
  - `_query_substitute_links`：`pm.number`→`pm.partnumber`
  - `_query_optional_links`：删除不存在的 `pul.component_partversion` join 条件
  - `_query_path_to_path_links`：`pathtopathlink` 无 `name`/`workspace_id` 列 → 改返回 []（PPL 域延后）

## 两大域已出独立计划
- 📋 **PathData/Path-to-Path**：`docs/superpowers/plans/2026-07-09-pathdata-domain.md`（15–20h）
- 📋 **Importer**：`docs/superpowers/plans/2026-07-09-importer-domain.md`（2–3 天）

---

## 零、迁移已完成的证据（无需担心的部分）

| 维度 | 结论 | 证据 |
|------|------|------|
| Nginx 生产入口 | Port 80 (host:8000) **18 个 location 全部指向 `back-py:8000`**，无一走 Payara | `docdoku-plm-docker/front/nginx.conf`（与容器内 `/etc/nginx/conf.d/default.conf` 一致） |
| 生产兜底 | 未匹配路由直接 `502`（暴露遗漏，不静默回退 Payara） | `front/nginx.conf:495-497` |
| CAD 转换回调 | 指向 FastAPI，不依赖 Payara | `docdoku-plm-docker/env/conversion.env` → `ENDPOINT=http://back-py:8000/...` |
| REST 资源覆盖 | 43 个 Java Resource + 5 个 BinaryResource **全部有对应 Python router**，无整域缺失 | `docdoku-plm-server-py/app/routers/*.py` |
| 迁移任务队列 | tracker.csv 523 条 100% 已完成 | `docs/migration/tracker.csv`（Model/DAO/Service 层） |
| 回归测试 | 176 passed / 1 skipped | `docdoku-plm-server-py` pytest |

> ⚠️ tracker.csv 追踪的是 **Model/DAO/Service 层文件迁移**，不覆盖 REST 路由层的功能完整性。本文件补充的正是 CSV 未体现的路由/功能层缺口。

---

## 一、🔴 P0 — PathData / Path-to-Path Link 域（最大缺口，跨层缺失）

这是唯一"Python 端点显著少于 Java"的域，且牵连多处降级。对 CATIA 装配路径级数据（路径实例属性、路径文件、路径间链接）是关键功能。

### 1.1 REST 端点缺失（`ProductInstancesResource` → `product_instances.py`，缺 ~17 个）

Java 25 个 HTTP 方法 → Python ~8 个独立路径。缺失清单：

| 状态 | Java 端点路径 | 说明 |
|------|-------------|------|
| ❌ | `GET .../instances/{sn}/pathdata/{path}` | 获取 pathdata |
| ❌ | `POST .../instances/{sn}/pathdata/{path}/new` | 创建 pathdata master |
| ❌ | `POST .../instances/{sn}/pathdata/{id}` | 创建 pathdata |
| ❌ | `PUT .../instances/{sn}/pathdata/{id}/iterations/{it}` | 更新 pathdata 迭代 |
| ❌ | `DELETE .../instances/{sn}/pathdata/{id}` | 删除 pathdata |
| ❌ | `PUT .../instances/{sn}/pathdata/.../files/{name}` | 更新 pathdata 文件 |
| ❌ | `DELETE .../instances/{sn}/pathdata/.../files/{name}` | 删除 pathdata 文件 |
| ❌ | `GET .../instances/{sn}/path-to-path-links-types` | 链接类型列表 |
| ❌ | `GET .../instances/{sn}/path-to-path-links` | 全部 PPL 链接 |
| ❌ | `GET .../instances/{sn}/path-to-path-links/{id}` | 单 PPL 链接 |
| ❌ | `GET .../path-to-path-links/source/{s}/target/{t}` | PPL 过滤查询 |
| ❌ | `GET .../path-to-path-links-roots/{type}` | PPL 根 |
| ❌ | `GET .../instances/{sn}/link-path-part/{p}` | 链接路径部件 |
| ❌ | `POST .../import` | 导入产品实例 |

### 1.2 BinaryResource 文件端点缺失（`ProductInstanceBinaryResource` → `product_files.py`，缺 ~3 个）

| 状态 | Java 端点 | 说明 |
|------|----------|------|
| ❌ | `POST .../pathdata/{id}/iterations/{it}` | 上传 pathdata 文件 |
| ❌ | `GET .../pathdata/{id}/{fn}` | 下载 pathdata 文件 |
| ❌ | `GET .../pathdata/{id}/iterations/{it}/{fn}` | 下载 pathdata 迭代文件 |

### 1.3 Service / ORM / DTO 层未实现

| 位置 | 缺失内容 | 工作量 |
|------|----------|--------|
| `app/models/configuration/path_data_master.py` | `PathDataMaster` ORM 字段不完整（缺 path、configuration_item 等） | 中 |
| `app/models/configuration/path_data_iteration.py` | `PathDataIteration` ORM 字段不完整 | 中 |
| `app/schemas/path_data_master.py` | `PathDataMasterDTO` 已定义但无填充 service | 大 |
| `app/schemas/path_data_iteration.py` | `PathDataIterationDTO` 已定义但无 CRUD | 大 |
| `app/schemas/path_data_iteration_creation.py` | `PathDataIterationCreationDTO` 已定义但创建接口未实现 | 大 |
| `app/ext/path_data_importer.py` | `PathDataImporter.parse()` 为 `@abstractmethod` 无具体实现 | 中 |
| `app/services/products/product_instance_manager.py:71-83` | `get_path_data_masters()` SQL 字段硬编码（按位置索引），可能与模型不一致 | 中 |

### 1.4 相关降级占位（返回空/硬编码，等 PathData 域实现后补齐）

| 位置 | 现状 | 影响 |
|------|------|------|
| `app/routers/products.py:527-538` | `ci_paths()` → `return []` | `GET .../products/{ci_id}/paths` |
| `app/routers/products.py:541-547` | `ci_document_links()` → `return []` | CI 文档链接查询 |
| `app/routers/products.py:325` | `path_choices()` 静默返回空（`PathDataMasterNotFoundException` 未抛） | 路径选择列表 |
| `app/routers/product_configurations.py:220-225` | `create_path_to_path_link()` → `{"id": -1, "status": "stub"}` | `POST .../path-to-path-links` |
| `app/routers/product_baselines.py:295-299` | `baseline_path_to_path_links_types()` → `return []` | 基线 PPL 类型 |
| `app/routers/product_baselines.py:302-307` | `baseline_path_to_path_links_detail()` → `return {}` | 基线 PPL 详情 |
| `app/services/product_structure.py:163` | `hasPathData` 硬编码 `False`（filter 遍历时不查询） | filter 结构组件 hasPathData |
| `app/services/product_structure.py:256` | `_check_has_path_data()` 已实现，但 config-spec 遍历时路径格式解析错误（总 False） | config-spec 遍历 |

> 相关异常已预留但未启用：`PathToPathCyclicException`、`PathToPathLinkAlreadyExistsException`、`PathToPathLinkNotFoundException`（`products.py:528-538` 注释标注"等待 PathData 域实现后抛出"）。

---

## 二、🟠 P1 — Importer 导入域（9 处全空壳，核心逻辑缺失）

| 位置 | 缺失内容 | 影响 API |
|------|----------|----------|
| `app/services/importer.py:11-17` | `import_into_parts()` → `{"partsImported": 0}`，不解析 Excel | `POST /parts/import` |
| `app/services/importer.py:19-26` | `dry_run_import_into_parts()` → 预览未实现 | 导入预览 |
| `app/services/importer.py:28-34` | `import_into_path_data()` → 路径数据导入未实现 | 路径数据批量导入 |
| `app/services/importer.py:36-42` | `import_bom()` → BOM 批量导入未实现 | BOM 导入 |
| `app/services/importer.py:44-51` | `dry_run_import_bom()` → BOM 预览未实现 | BOM 导入预览 |
| `app/routers/parts.py:352` | `GET .../parts/imports/{filename}` → `return {}` | 导入状态查询 |
| `app/routers/parts.py:361` | `GET .../parts/import/{import_id}` → `return {}` | 导入结果查询 |
| `app/routers/parts.py:371` | `POST /parts/import` → 仅生成 import_id，不做实际导入 | 零件导入 |
| `app/routers/parts.py:381` | `POST /parts/importPreview` → 同上 | 导入预览 |

工作量：**大**（全部核心逻辑缺失，需 Excel 解析 + Bulk Import）。

---

## 三、🟡 P2 — 产品配置 / 基线数据降级（✅ 2026-07-09 已完成）

以下原硬编码 `[]` 的 `substitutesParts`/`optionalsParts` 已用 decode_path 真实填充；`substituteLinks`/`optionalUsageLinks` 已从路径表读取。config `substituteLinks` schema 已改 `List[str]` 对齐 Payara。

| 位置 | 原字段 | 状态 |
|------|-------|------|
| `product_configurations.py` `_config_to_dict`/list/list_ci | 四字段 | ✅ 已填充 |
| `product_baselines.py` `_bl_summary_dict`/`_bl_detail_dict` | substitutesParts/optionalsParts | ✅ 已填充 |

---

## 四、🟡 P2 — Product Structure 组件降级（✅ 2026-07-09 大部完成）

| 位置 | 内容 | 状态 |
|------|------|------|
| `product_structure.py` `_build_component` | `attributes`（实例属性）| ✅ 真实查询 |
| `product_structure.py` `_build_component`/`_convert_visitor_component` | `notifications` | ✅ 真实查询 |
| `product_structure.py` `_convert_visitor_component` | `attributes` | ✅ 真实查询 |
| `products.py` `_ci_to_dict` | `hasModificationNotification` | ✅ 真实查询 |
| `product_structure.py` config-spec 遍历 `hasPathData` | 仍 False | ⏳ 随 PathData 域（见计划 Task 8）|

---

## 五、🟢 P3 — 小型单表 STUB（✅ 2026-07-09 大部完成）

### 5.1 WorkspaceManager（✅ 已完成 — 改为真实实现 + 路由委派）
tracker.csv 映射 `WorkspaceManagerBean.java → workspace_manager.py`，Payara 该 Bean 的 `getDiskUsageInWorkspace`/`getWorkspaceFrontOptions`/`updateWorkspaceFrontOptions`/`getWorkspaceBackOptions`/`updateWorkspaceBackOptions` 均为**真实方法**。按对齐 Payara 铁律，`workspace_manager.py` 现已改为真实实现（原为 stub，违反映射），并将 `workspaces.py` 路由改为委派 service（对齐 Payara `WorkspaceResource → WorkspaceManagerBean → DAO` 分层）。前端 workspace 信息（disk usage/文档数/零件数/成员）本就由 workspaces.py 路由真实提供，此次消除了重复逻辑。

### 5.2 Query 查询（✅ 读/删完成，创建=执行引擎延后）
- ✅ `get_queries()`：真实查询（含递归 queryrule 树 + selects/orderBy/groupedBy/contexts）
- ✅ `delete_query()`：真实级联删除（子表 + 递归 queryrule 树）
- ⏳ `post_workspace_query()`/`post_queries()` = Java `runCustomQuery`（**查询执行引擎**：递归 rule 树 → 结果集），非简单 CRUD。见新 loose-end「Query 执行引擎」。

### 5.3 OnDemandConverter（⏳ deferred — 需外部引擎）
`get_document_converted_resource`/`get_part_converted_resource` 依赖 LibreOffice/jodconverter（Java `OfficeOnDemandConverter`），容器内无此引擎，且无 Python 调用方。已明确注释：无引擎时返回空（对齐 Payara null 行为）。

### 5.4 EffectivityDTO（✅ 已完成）
空壳 schema 已填充全字段（id/name/description/configurationItemNumber/workspaceId/typeEffectivity + date/number/lot 起止字段），对齐 Payara + 路由实际输出。

---

## 六、⚙️ 基础设施 loose ends

| 项 | 现状 | 影响 / 建议 |
|----|------|-------------|
| ~~SSL Proxy (9000→443 HTTPS)~~ | ✅ 2026-07-09 已切 FastAPI（指向 front）；附带修复丢失的 cert.key | — |
| ~~DocumentBaselines 端点缺 3 个~~ | ✅ 2026-07-09：补 `GET /{id}` + `/{id}-light`；export-files 早已存在 | — |
| **Payara 容器保留** | 作为 Port 85 (host:8005) 对比端点，设计如此 | 迁移验证期保留，无需处理 |

---

## 六之二、🆕 2026-07-09 新发现 loose ends

| 项 | 位置 | 说明 | 工作量 |
|----|------|------|--------|
| **Query 执行引擎** | `parts.py` `post_workspace_query`/`post_queries` | Java `runCustomQuery`：递归 QueryRule 树 → 动态查询 part 结果集（+可选 save）。当前仅做重名检查返回 `{"id":0}`。需实现规则→SQL 编译器。 | 大 |
| **filter configSpec 解析** | `products.py:141` `filter_structure` / `product_structure.py:112` | `configSpec` 字符串（"latest"/"released"/"wip"/baseline-id）直接传给 PSFilterVisitor，未解析为 ProductConfigSpec 对象 → 有 configSpec 时 500（`'str' object has no attribute 'filter_part_iterations'`）。全量遍历（无 configSpec）正常。 | 中 |

---

## 七、非缺陷项（接口设计，已确认无需处理）

以下 `raise NotImplementedError` 均为抽象基类接口，对应具体子类已完整实现：

- `app/models/configuration/product_structure_filter.py:16-22` — `filter_part_iterations()` / `filter_links()`
- `app/models/configuration/product_config_spec.py:34-40` — `filter_part_iteration()` / `filter_part_link()`
- `app/services/configuration/spec/effectivity_config_spec.py:82-84` — `is_effective()`（Date/Serial/Lot 子类均已实现）

---

## 八、剩余工作优先级（2026-07-09 更新）

| 优先级 | 项 | 计划/状态 | 工作量 |
|--------|-----|----------|--------|
| 1 | **PathData / Path-to-Path 域**（第一节） | 📋 `plans/2026-07-09-pathdata-domain.md` | 大 (15-20h) |
| 2 | **Importer 域**（第二节） | 📋 `plans/2026-07-09-importer-domain.md` | 大 (2-3天) |
| 3 | **Query 执行引擎**（六之二） | 待排期 | 大 |
| 4 | **filter configSpec 解析**（六之二） | 待排期 | 中 |
| 5 | **OnDemandConverter**（5.3） | deferred（需 LibreOffice 引擎） | 中 |
| — | ~~A/B/C 批次~~ | ✅ 2026-07-09 完成 | — |

## 九、统计汇总（2026-07-09 更新）

| 域 | 状态 |
|----|------|
| 基础设施（SSL Proxy/DocumentBaselines）| ✅ 完成 |
| 产品配置/基线降级 | ✅ 完成 |
| Product Structure 降级 | ✅ 完成（config-spec hasPathData 随 PathData 域）|
| WorkspaceManager / Query 读删 / EffectivityDTO | ✅ 完成 |
| 3 个 pre-existing 生产 SQL bug | ✅ 修复 |
| PathData / Path-to-Path | ⏳ 出计划 |
| Importer | ⏳ 出计划 |
| Query 执行引擎 / filter configSpec / OnDemandConverter | ⏳ 待排期 |

> 主干业务（认证/零件/文档/变更/工作流/用户组/产品结构/基线/配置）已完整迁移。剩余为 **装配路径(PathData)**、**批量导入(Importer)**、**自定义查询执行**、**配置规格过滤** 四个功能面。
