# Importer 导入域迁移实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: 用 superpowers:executing-plans 逐任务执行。步骤用 checkbox 跟踪。

**Goal:** 将 Payara 的零件属性导入（Excel）迁移到 FastAPI，实现 `importIntoParts` + `dryRunImportIntoParts` + PathData 属性导入，补齐 5 个 REST 端点。

**Architecture:** openpyxl 解析 .xlsx（cell-comment 元数据）→ 校验 → 创建/更新 part attributes。对齐 Payara `ImporterBean` + `PartAttributesImporterImpl` + `ExcelParser`。

**Tech Stack:** FastAPI, openpyxl, SQLAlchemy。

**预估工作量：2–3 天（~1100 行）**

## Global Constraints（铁律）
- **对齐 Payara**：解析规则、校验、DTO 以 `docdoku-plm-server-attributes-importer/.../ExcelParser.java`、`ImporterBean.java`、`PartsResource.java` 为准。
- **不能 rebuild**：`docker cp` + restart。
- **测试基线**：176 passed / 1 skipped 不退化。

---

## 拦路虎 / 前置决策
1. **openpyxl 依赖**（高，非硬阻塞）：容器内无 openpyxl；requirements.txt 也没有。宿主机有 3.1.5。
   - 方案：`pip3 download openpyxl -d /tmp/whl` → `docker cp /tmp/whl/*.whl back-py:/tmp/` → `docker exec back-py pip install --no-index --find-links /tmp /tmp/openpyxl*.whl`。同时把 `openpyxl==3.1.5` 加进 requirements.txt（为将来 rebuild）。
   - 注意：indexer_text_extractor.py 已用 openpyxl，说明生产镜像**可能已装**——先 `docker exec back-py python -c "import openpyxl"` 确认。
2. **.xls vs .xlsx**（中）：Java 只收 `.xls`（`EXTENSIONS={"xls"}`），openpyxl 只支持 `.xlsx`。决策：Python 侧只接受 `.xlsx`（用户另存），底层 POI 本就能读 xlsx。
3. **cell-comment 元数据**（高）：表头/值单元格的 comment 承载属性类型元数据（`名称 <类型> <LOV名>`）。openpyxl 读 `ws.cell(r,c).comment.text`。**先抓一份线上真实导入 Excel 确认 comment 格式**。
4. **BOM 导入**：Java `BomImporter` 接口无实现类，`doBomImport` 死代码 → **不迁移**，保持 stub。

---

## Task 0 — 依赖与样本确认（前置）

> **2026-07-10 调研已确认的现状（无需重复确认）：**
> - `requirements.txt` **无 openpyxl**（仅 `indexer_text_extractor.py` 用 try/except 延迟导入）。
> - `app/services/importer.py`：`ImporterService` + 6 方法全 STUB，模块级单例 `importer_service`，**零外部引用**（孤立）。
> - `app/routers/parts.py:447-491`：5 个 import 端点全空壳/假动作，**不调用 service**，POST 端点**未注入 `db`**。
> - ORM `app/models/product/import_.py`（`Import`→表 `import`）已存在；`app/schemas/import_.py`(`ImportDTO`) + `import_preview.py`(`ImportPreviewDTO`) 已存在但未被使用。
> - `app/ext/` 已有 `PartImporter`/`BomImporter`/`PathDataImporter` 抽象基类（含 parse/validate），无具体实现。
> - **无真实 Excel 样本**（用户确认）→ 决策：按 `ExcelParser.java` 规范尽力实现，用**合成 .xlsx 夹具**（openpyxl 写带 cell-comment 的测试文件）做单测。

- [ ] `docker exec docdoku-plm-docker-back-py-1 python -c "import openpyxl; print(openpyxl.__version__)"` 确认是否已装
- [ ] 若未装：`pip3 download openpyxl -d /tmp/whl` → `docker cp /tmp/whl/*.whl back-py:/tmp/` → `docker exec back-py pip install --no-index --find-links /tmp /tmp/openpyxl*.whl`
- [ ] `openpyxl==3.1.5` 加入 requirements.txt
- [ ] 新建合成样本夹具 `tests/fixtures/make_import_xlsx.py`：用 openpyxl 生成带表头 `名称 <类型>` / `名称 <ListOfValues> LOV名` 及首列 cell-comment `pm.number` 的 .xlsx，对齐 `ExcelParser.java` 的解析假设

## Task 1 — Excel 解析器（高，~500 行）
文件：新建 `app/services/importers/excel_parser.py`。对齐 `ExcelParser.java`：
- [ ] 表头正则：`(.*) <(.*)> <(.*)>`（新 LOV）、`(.*) <(.*)>`（新属性）
- [ ] 首列校验：parts 导入首列 `pm.number`；pathdata 导入前三列 `ctx.productId`/`ctx.serialNumber`/`pm.number`（cell comment 标识）
- [ ] 属性类型：Text/Number/Date/Boolean/URL/Long_Text + LOV
- [ ] 多值 `|` 分隔 + 多 comment
- [ ] 校验 `checkFile()`：空文件/重复名/类型不支持/类型值不匹配/日期格式 `yyyy-MM-dd HH:mm:ss`

## Task 2 — 属性转换工具（中，~200 行）
文件：新建 `app/services/importers/attributes_importer_utils.py`。对齐 `AttributesImporterUtils.java`：
- [ ] Attribute → InstanceAttribute 子类（按类型建 dtype）
- [ ] `updateAndCreateInstanceAttributes`：按 name+type 判断更新 vs 新建
- [ ] LOV 值查 `listofvalues` 表校验

## Task 3 — Import ORM + DTO（低，~140 行）
- [ ] 新建 `app/models/product/import_record.py`：`IMPORT` + `IMPORT_WARNING`/`IMPORT_ERROR` ElementCollection 表
- [ ] DTO：`ImportDTO{id,fileName,startDate,endDate,succeed,pending,errors,warnings}`、`ImportPreviewDTO{partRevsToCheckout,partsToCreate}`

## Task 4 — ImporterService 实现（中高，~250 行）
文件：`app/services/importer.py`（替换 5 个 stub）。对齐 `ImporterBean.doPartImport` + `bulkPartUpdate`：
- [ ] `import_into_parts`：解析 → 遍历 part（查存在/写权限/checkout 锁/permissive）→ 合并属性 → autoCheckout/update/autoCheckin
- [ ] `dry_run_import_into_parts`：解析 + 判断需 checkout 的 part，不写入
- [ ] `import_into_path_data`：三级定位 productId/serialNumber/path（依赖 PathData 域，可后置）
- [ ] BOM 两方法保持 stub（Java 无实现）

## Task 5 — REST 端点（低，~60 行）
文件：`app/routers/parts.py`（替换 stub，行 346-388）。对齐 `PartsResource`：
- [ ] `POST /workspaces/{ws}/parts/import`（multipart + autoCheckout/autoCheckin/permissiveUpdate/revisionNote/importType）
- [ ] `POST /workspaces/{ws}/parts/importPreview`
- [ ] `GET /workspaces/{ws}/parts/imports/{filename}` / `import/{id}` / `DELETE import/{id}`（读写 IMPORT 表）
- [ ] 修正 URL 加 workspace_id 前缀（当前 stub 缺）

## 收尾
- [ ] 全量 pytest ≥176 passed + 新增 importer 单测（用真实样本 xlsx）
- [ ] docker cp（含依赖安装）+ restart + 线上冒烟（上传 xlsx → preview → import → 校验属性写入）
- [ ] 更新 `docs/migration/loose-ends.md`（勾选第二节）+ CHANGELOG + REMINDERS
