# FastAPI 迁移遗留清单（Migration Loose Ends）

> 生成日期：2026-07-08
> 范围：Java EE Payara (`docdoku-plm-server`) → FastAPI (`docdoku-plm-server-py`) 后端迁移
> 状态：**核心业务已 100% 走 FastAPI，Payara 在生产链路已被完全绕过**，剩余为功能性 loose ends
>
> 本文件汇总所有未完成/占位/降级项，作为后续收尾的唯一清单。修复某项后请在本文件勾选并同步 `CHANGELOG.md` / `REMINDERS.md`。

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

## 三、🟡 P2 — 产品配置 / 基线数据降级（6 处，字段硬编码空）

| 位置 | 硬编码为 `[]` 的字段 | 影响 |
|------|---------------------|------|
| `app/routers/product_configurations.py:73-76` | `substituteLinks`, `optionalUsageLinks`, `substitutesParts`, `optionalsParts` | 产品配置详情缺替代件/可选件 |
| `app/routers/product_configurations.py:107-111` | 同上（`list_configs()`） | 产品配置列表 |
| `app/routers/product_configurations.py:126-130` | 同上（`list_ci_configs()`） | CI 产品配置列表 |
| `app/routers/product_baselines.py:58-59` | `substitutesParts`, `optionalsParts`（`_bl_summary_dict()`） | 基线摘要 |
| `app/routers/product_baselines.py:79-80` | `substitutesParts`, `optionalsParts`（`_bl_detail_dict()`） | 基线详情 |

> 注：baseline 中 `substituteLinks`/`optionalUsageLinks` 有实际查询（`_query_substitute_links`/`_query_optional_links`），仅 `substitutesParts`/`optionalsParts` 为空；product_configurations 中四字段全空。

---

## 四、🟡 P2 — Product Structure 组件降级（4 处）

| 位置 | 降级内容 | 影响 |
|------|----------|------|
| `app/services/product_structure.py:165` | `"attributes": []`（filter 遍历不查实例属性） | filter 结构无属性 |
| `app/services/product_structure.py:168` | `"notifications": []`（filter 遍历不查通知） | filter 结构无修改通知 |
| `app/services/product_structure.py:258` | `"attributes": []`（全量遍历也不查实例属性） | 结构组件无自定义属性 |
| `app/routers/products.py:65` | `"hasModificationNotification": False` 硬编码 | CI 列表/详情 |

---

## 五、🟢 P3 — 小型单表 STUB

### 5.1 WorkspaceManager（5 处，均单表 CRUD，工作量小）

| 位置 | 缺失内容 |
|------|----------|
| `app/services/workspace_manager.py:88-91` | `get_disk_usage()` → 返回 0，未做 vault 磁盘计算 |
| `app/services/workspace_manager.py:93-95` | `get_workspace_front_options()` → 未读 `workspacefrontoptions` 表 |
| `app/services/workspace_manager.py:97-100` | `update_workspace_front_options()` → 未写 `workspacefrontoptions` 表 |
| `app/services/workspace_manager.py:102-104` | `get_workspace_back_options()` → 未读 `workspacebackoptions` 表 |
| `app/services/workspace_manager.py:106-109` | `update_workspace_back_options()` → 未写 `workspacebackoptions` 表 |

### 5.2 Query 查询（4 处，工作量小）

| 位置 | 缺失内容 |
|------|----------|
| `app/routers/parts.py:250-253` | `get_queries()` → `return []`，不查库 |
| `app/routers/parts.py:260-278` | `post_workspace_query()` → 只检查重名返回 `{"id": 0}`，不创建 |
| `app/routers/parts.py:281-301` | `post_queries()` → 同上 |
| `app/routers/parts.py:304-308` | `delete_query()` → 直接 204，不删库 |

### 5.3 OnDemandConverter（2 处，工作量中）

| 位置 | 缺失内容 |
|------|----------|
| `app/services/ondemand_converter.py:11-16` | `get_document_converted_resource()` → 返回空 bytes |
| `app/services/ondemand_converter.py:18-23` | `get_part_converted_resource()` → 返回空 bytes |

### 5.4 EffectivityDTO（1 处，工作量小）

| 位置 | 缺失内容 |
|------|----------|
| `app/schemas/misc/effectivity.py:7-10` | `EffectivityDTO` 空壳（仅 `pass`）。注：`effectivity.py` 的 CRUD 端点实为完整实现，返回 dict 而非该 DTO，功能可用，仅 DTO 未填充 |

---

## 六、⚙️ 基础设施 loose ends

| 项 | 现状 | 影响 / 建议 |
|----|------|-------------|
| **SSL Proxy (9000→443 HTTPS)** | `docdoku-plm-docker/proxy/nginx.conf:22-34` — API + WebSocket **全量走 Payara `back:8080`**，尚未更新 | ⚠️ 若生产用 HTTPS，用户实际未用上 FastAPI。**低风险高价值收尾项**：复制 Port 80 的 location 规则即可 |
| **DocumentBaselines 端点缺 3 个** | `document_baselines.py` 缺 `GET /{id}`（单基线详情）、`GET /{id}-light`、`GET /{id}/export-files` | 基线详情/导出功能不可用 |
| **Payara 容器保留** | 作为 Port 85 (host:8005) 对比端点，设计如此 | 迁移验证期保留，无需处理 |

---

## 七、非缺陷项（接口设计，已确认无需处理）

以下 `raise NotImplementedError` 均为抽象基类接口，对应具体子类已完整实现：

- `app/models/configuration/product_structure_filter.py:16-22` — `filter_part_iterations()` / `filter_links()`
- `app/models/configuration/product_config_spec.py:34-40` — `filter_part_iteration()` / `filter_part_link()`
- `app/services/configuration/spec/effectivity_config_spec.py:82-84` — `is_effective()`（Date/Serial/Lot 子类均已实现）

---

## 八、修复优先级建议

| 优先级 | 项 | 理由 | 工作量 |
|--------|-----|------|--------|
| 1 | **SSL Proxy 切 FastAPI**（第六节） | 低风险、高价值，仅改 nginx 配置 | 小 |
| 2 | **PathData / Path-to-Path 域**（第一节） | 最大功能缺口，CATIA 协同设计关键 | 大 |
| 3 | **产品配置/基线 substitutesParts/optionalsParts**（第三节） | 数据完整性，用户可见 | 中 |
| 4 | **Product Structure attributes/notifications**（第四节） | 结构树属性缺失 | 中 |
| 5 | **Importer 域**（第二节） | 功能完整但使用频率待评估 | 大 |
| 6 | **DocumentBaselines 3 端点**（第六节） | 基线详情/导出 | 小 |
| 7 | **WorkspaceManager / Query / OnDemandConverter 小 stub**（第五节） | 边角功能 | 小 |

---

## 九、统计汇总

| 域 | 待修项 | 工作量 |
|----|:--:|:--:|
| PathData / Path-to-Path（第一节） | ~25 | 大 |
| Importer（第二节） | 9 | 大 |
| 产品配置/基线降级（第三节） | 6 | 中 |
| Product Structure 降级（第四节） | 4 | 中 |
| WorkspaceManager / Query / Converter / Effectivity（第五节） | 12 | 小 |
| 基础设施（第六节） | 3 类 | 小-中 |
| **合计需修** | **~59 处** | 核心：PathData → Importer |

> 全部集中在 **产品实例 / 装配路径 / 导入** 三个功能面，用户认证、零件、文档、变更、工作流、用户组等主干业务已完整迁移。
