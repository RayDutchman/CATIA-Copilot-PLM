# PathData / Path-to-Path Link 域迁移实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: 用 superpowers:executing-plans 逐任务执行。步骤用 checkbox 跟踪。

**Goal:** 将 Payara 的 PathData（装配路径级实例数据）与 Path-to-Path Link（路径间链接）域完整迁移到 FastAPI，补齐 18 个 REST 端点 + 3 个文件端点 + Service/ORM/DTO 层。

**Architecture:** SQLAlchemy raw SQL + ORM 修复。对齐 Payara `ProductInstanceManagerBean` / `ProductManagerBean` 的 pathdata/pathToPath 方法。部署走 `docker cp` + restart back-py。

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL, 文件 vault 存储。

**预估工作量：15–20h（2.5–3 天）**

## Global Constraints（铁律）
- **对齐 Payara**：字段名/类型/DTO/异常以 Java 源码为准（`docdoku-plm-server-rest/.../rest/dto/product/*`、`ProductInstanceManagerBean.java`、`ProductManagerBean.java`）。
- **不能 rebuild**：`docker cp` + `docker restart docdoku-plm-docker-back-py-1`。
- **extra=forbid**：helper 返回 dict 前逐字段核对 schema。
- **测试基线**：pytest 176 passed / 1 skipped 不退化。
- 数据库表已存在且当前为空（`pathdatamaster`/`pathdataiteration`/`pathtopathlink` 均 0 行），测试无破坏风险。

---

## 关键 DB 结构（已核实）
```
pathdatamaster:      id(PK,serial), path(varchar255)          # 无 workspace/ci 列
pathdataiteration:   iteration(PK), dateiteration(ts), iterationnote(text),
                     pathdatamaster_id(PK,FK)                 # 复合主键(pathdatamaster_id,iteration)
pathtopathlink:      id(PK,serial), type, sourcepath, targetpath, description  # 无 name/workspace 列
连接表: prdinstiteration_pathdatamstr / prdinstiteration_p2plink /
        configurationitem_p2plink / productbaseline_p2plink /
        pathdataiteration_attribute / pathdataiteration_binres / pathdataiteration_documentlink
```

## 拦路虎（务必先解决）
1. **复合主键**：`PathDataIteration` 是 `(pathdatamaster_id, iteration)` 复合主键，现有 ORM 用 autoincrement `id` 且含 DB 不存在的列 → 需推倒重建。
2. **环检测**：`createPathToPathLink` 抛 `PathToPathCyclicException`，需实现有向图环检测（DFS/BFS，对齐 Java `findNextPathToPathLinkInProduct`）。
3. **rebase 级联拷贝**：`copyPathDataMasterList` 深拷贝含附件二进制 `storageManager.copyData`。
4. **文件存储**：PathData 附件 vault 路径 `{ws}/product-instances/{sn}/pathdata/{id}/iterations/{it}/{filename}`。
5. **属性一致性**：`updatePathData` 调 `AttributesConsistencyUtils.hasValidChange()`（Python 已有等价，见 product_manager.py）。

---

## Task 1 — ORM 模型重建（P0 前置，中，2-3h）
- [ ] 重建 `app/models/configuration/path_data_master.py`：仅 `id`、`path`；删除 DB 不存在的 workspace_id/creationdate/author_*；加 relationship 到 iterations 与 secondary(`prdinstiteration_pathdatamstr`)→ProductInstanceIteration
- [ ] 重建 `app/models/configuration/path_data_iteration.py`：复合主键 `(pathdatamaster_id, iteration)`；字段 `dateiteration`/`iterationnote`；删除 DB 不存在列；加 3 relationship（attributes/documents/files via 关联表）
- [ ] 修 `app/models/product/path_to_path_link.py`：字段对齐（id/type/sourcepath/targetpath/description）；加 3 secondary 关联
- [ ] `python -c "import app.main"` 通过

## Task 2 — DTO 微调（P2，低，15min）
- [ ] `app/schemas/path_to_path_link.py`：补 `sourcePath`/`targetPath`（当前只有 sourceComponents/targetComponents）
- [ ] 核对 `PathDataMasterDTO`/`PathDataIterationDTO`/`PathDataIterationCreationDTO` 与 Java 对齐

## Task 3 — Service: PathData CRUD（P1，高，3-4h）
文件：`app/services/products/product_instance_manager.py`。对齐 Java `ProductInstanceManagerBean`：
- [ ] 修复 `get_path_data_masters()`（现按位置索引硬编码，列名错误）
- [ ] `get_path_data_by_path(ws, ci, sn, path)` → 查 PathDataMaster
- [ ] `create_path_data_master(...)` → 新建 master + 首 iteration（路径已存在则加 iteration）
- [ ] `add_new_path_data_iteration(...)` → 复制上一 iteration 附件/属性/note
- [ ] `update_path_data(...)` → 更新 attributes/note/linkedDocuments + hasValidChange 校验
- [ ] `delete_path_data(...)` → 移除 master + 级联删附件文件与 DB

## Task 4 — Service: PathToPathLink（P1，高，含环检测 2h）
文件：`app/services/products/product_manager.py` + `product_instance_manager.py`：
- [ ] `get_path_to_path_link(id)` / `get_path_to_path_link_types()` / `get_path_to_path_links()`
- [ ] `get_path_to_path_link_from_source_and_target(s,t)`（双向）/ `get_root_path_to_path_links(type)`
- [ ] `create_path_to_path_link(...)` **含环检测** → 抛 `PathToPathCyclicException`
- [ ] `update_path_to_path_link(id, desc)` / `delete_path_to_path_link(id)`
- [ ] 启用预留异常 `PathToPathCyclicException`/`PathToPathLinkAlreadyExistsException`/`PathToPathLinkNotFoundException`

## Task 5 — Router: PathData 端点（P2，中，2h）
文件：`app/routers/product_instances.py`。补 8 个端点（对齐 Java `ProductInstancesResource` 行 487-990）：
- [ ] `GET /instances/{sn}/pathdata/{path}`
- [ ] `POST /instances/{sn}/pathdata/{path}/new`
- [ ] `POST /instances/{sn}/pathdata/{id}`（新 iteration）
- [ ] `PUT /instances/{sn}/pathdata/{id}/iterations/{it}`
- [ ] `DELETE /instances/{sn}/pathdata/{id}`
- [ ] `PUT/DELETE /instances/{sn}/pathdata/{id}/iterations/{it}/files/{name}`

## Task 6 — Router: PathToPathLink 端点（P2，中，1.5h）
- [ ] `product_instances.py` 补 6 个查询端点（types/links/{id}/source-target/roots/link-path-part）
- [ ] `products.py` 补 CI 级 CRUD（POST/PUT/DELETE/GET source-target），替换 `ci_paths`/`ci_document_links` 的 `return []`
- [ ] `product_configurations.py:220` `create_path_to_path_link` stub → 真实实现
- [ ] `product_baselines.py` `baseline_path_to_path_links_types/detail` → 真实（复用 `_query_path_to_path_links` 现已返回 []，改为真实查询）

## Task 7 — 文件存储层（P2，中，2h）
- [ ] PathData 附件上传/下载/重命名/删除（vault 路径对接 binary_storage）
- [ ] `product_files.py` 补 3 端点：`POST pathdata/{id}/iterations/{it}`、`GET pathdata/{id}/{fn}`、`GET pathdata/{id}/iterations/{it}/{fn}`

## Task 8 — 降级点回填（P2）
- [ ] `product_structure.py:_check_has_path_data` config-spec 遍历路径解析（当前 config-spec 时总 False）
- [ ] `product_structure.py` filter 遍历时 `hasPathData` 真实查询（当前硬编码 False）

## 收尾
- [ ] 全量 pytest ≥176 passed
- [ ] 新增 pathdata/pathToPath 单元测试
- [ ] docker cp + restart + 线上冒烟（创建 pathdata → 查询 → 加 iteration → 删除；创建 p2p link → 环检测）
- [ ] 更新 `docs/migration/loose-ends.md`（勾选第一节）+ CHANGELOG + REMINDERS
