# ES 全文搜索——Payara → FastAPI 迁移映射表

> **本文件性质**：这是一份**迁移映射表**，不是实现说明。
>
> **唯一事实源**：`docdoku-plm-server/` 下的 28 个 Java 文件 + 3 个 JSON 索引模板。任何字段名、索引名、行为，以 Java 源码为准；本表只负责把 Java 单元锚定到 Python 目标文件。
>
> **保真档位**：完全字面保真（用户 2026-07-06 决策）。索引命名、mapping、iteration 粒度、docId 编码、nested 查询全部原样复刻。
>
> **实现者须知**：写 Python 前先打开对应 Java 文件读真源码，**不要照抄本表里的任何伪代码**——本表的代码片段仅用于定位，可能与最终实现有出入。字段名冲突时，一律回到 Java 源码 + `IndexerMapping.java` 常量 + 3 个 JSON 模板核对。

---

## 〇、事实源文件清单（28 Java + 3 JSON）

### 索引核心包 `docdoku-plm-server-ejb/.../indexer/`

| Java 文件 | 行数 | 职责 | Python 目标 |
|-----------|------|------|------------|
| `IndexerManagerBean.java` | 486 | 业务层：实时索引 / 搜索 / 批量重建 | `app/services/indexer_manager.py` |
| `IndexManagerBean.java` | 289 | 低层 ES 客户端封装：建/删索引、search、bulk、update、delete | 合并进 `indexer_manager.py` |
| `IndexerQueryBuilder.java` | 280 | 构建 update 请求 + search 查询 | `app/services/es_query_builder.py`（search）+ `indexer_manager.py`（update doc 构建） |
| `IndexerResultsMapper.java` | 190 | ES SearchResult → IterationKey → DB 实体 | `es_query_builder.py` 返回 key，router 查 DB |
| `IndexerTextExtractor.java` | — | 附件全文提取（PDF/DOC/XLS） | ⏸ 登记 REMINDERS（重型可选） |
| `util/EntityMapper.java` | — | 实体 → ES JSON doc（写入内容的唯一事实） | `indexer_manager.py` 的 `_part_to_doc`/`_doc_to_es_doc` |
| `util/IndexerMapping.java` | 67 | 字段名常量 + 索引名常量 | `indexer_manager.py` 顶部常量 |
| `util/IndicesUtils.java` | 81 | 索引名生成 + docId 格式化 | `indexer_manager.py` 的 `_index_name`/`_format_doc_id` |
| `client/IndexerClientProducer.java` | — | Jest 客户端工厂（basic auth / AWS IAM） | `indexer_manager.py` 的 `es` property（basic 部分） |

### ES 索引模板 JSON（mapping 唯一事实源，字面复用）

| JSON 文件 | order | 匹配模式 | 说明 |
|-----------|-------|----------|------|
| `resources/.../indexer/common-template.json` | 0 | `*-docdoku-plm-*` | 共享 15 字段 + nested attributes/files |
| `resources/.../indexer/document-template.json` | 1 | `*-docdoku-plm-*-documents` | 文档特有 docMId/folder/title + id_analyzer |
| `resources/.../indexer/part-template.json` | 1 | `*-docdoku-plm-*-parts` | 部件特有 partName/partNumber/standardPart + id_analyzer |

### 查询类 `docdoku-plm-server-core/.../query/`

| Java 文件 | Python 目标 |
|-----------|------------|
| `SearchQuery.java`（父类，13 getter + AttributeQuery 子类） | `es_query_builder.py` 参数处理 |
| `DocumentSearchQuery.java`（docMId/title/folder） | `es_query_builder.py` `search_documents` |
| `PartSearchQuery.java`（partNumber/name/standardPart） | `es_query_builder.py` `search_parts` |

### REST 层 `docdoku-plm-server-rest/.../rest/`

| Java 文件 | Python 目标 |
|-----------|------------|
| `PartsResource.searchPartRevisions:206` | `app/routers/parts.py` `search_parts:77` |
| `DocumentsResource.searchDocumentRevision:115` | `app/routers/documents.py` `search_documents:28` |
| `AdminResource.indexWorkspaceData:248` / `indexAllWorkspaces:266` | `app/routers/admin.py` `put_index:370`（现为 stub） |
| `WorkspaceResource.synchronizeIndexer:274` | `app/routers/workspaces.py`（reindex 端点，现为 stub） |
| `util/SearchQueryParser.java` | 融入各 router 的查询参数解析 |

### 实时索引触发点（业务 Bean）

| Java 文件 | Python 目标 |
|-----------|------------|
| `ProductManagerBean.java`（checkInPart / deletePartRevision） | `app/services/product_manager.py` |
| `DocumentManagerBean.java`（checkInDocument / moveDocumentRevision / moveFolder / deleteDocumentRevision） | `app/services/document_manager.py` |
| `WorkspaceManagerBean.java`（createWorkspace / doDeleteWorkspace） | `app/routers/workspaces.py` |

---

## 一、索引生命周期管理

### 1.1 索引命名规则（IndicesUtils.java:46）——⚠️ 与旧文档完全不同

**Java 事实**（`IndicesUtils.getIndexName` + `formatIndexName`）：
```java
// 行 46-49
return config.getPrefixIndex() + "-" + "docdoku-plm" + "-" + formatIndexName(workspaceId) + "-" + type;
// 行 58-65: formatIndexName = URLEncoder.encode(Tools.unAccent(workspaceId), "UTF-8").toLowerCase()
```
- `prefixIndex` 来自 `IndexerConfig.getPrefixIndex()`，默认 `"localhost"`
- 结果示例：`localhost-docdoku-plm-w1-parts`、`localhost-docdoku-plm-w1-documents`
- workspaceId 先 unaccent（`é→e`）→ URL 编码（空格→`+`）→ 小写

| Java | Python 目标 | 复刻要点 |
|------|------------|---------|
| `getIndexName(ws, INDEX_PARTS)` | `_part_index_name(ws)` | 必须复刻完整前缀 + unaccent + urlencode + lower |
| `getIndexName(ws, INDEX_DOCUMENTS)` | `_doc_index_name(ws)` | 同上 |
| `config.getPrefixIndex()` | `settings.ES_INDEX_PREFIX`（新增，默认 `"localhost"`） | 需新增配置项 |

> **决策**：前缀默认 `"localhost"` 与 Payara 一致。若两套系统共用同一 ES 且要复用 Payara 已建索引，前缀必须与 Payara 部署时的 `IndexerConfig` 一致。

### 1.2 索引 mapping（3 个 JSON 模板，字面复用）

**Java 事实**（`IndexManagerBean.init:73` @PostConstruct）：启动时用 `PutTemplate` 注册 3 个模板到 ES，索引按模板匹配模式自动套用 mapping。**mapping 不写在 Java 代码里，写在 3 个 JSON 模板中。**

| Java | Python 目标 | 复刻要点 |
|------|------------|---------|
| `initTemplate("docdoku-plm-common", common-template.json)` | 启动时 `es.indices.put_template("docdoku-plm-common", <json>)` | **原样复用 JSON**：把 3 个模板文件复制到 Python 项目 resources，或内联为 dict。带 `id_analyzer`（char_group tokenizer，按 whitespace/`-`/`_`/`\n` 切分）、nested attributes/files |
| `createIndices(ws)`（行 90，创建 documents+parts 两个空索引，mapping 由模板提供） | `create_index(ws)` | 创建时**不带 mapping body**，靠模板匹配 |
| `deleteIndices(ws)`（行 102） | `delete_index(ws)` | 删两个索引 |
| `indicesExist(ws)`（行 219，OR 逻辑） | 复刻 exists 判断 | |

**完整 mapping（合并后，字面保真目标）**——共享 15 字段：
`workspaceId(keyword)`, `attributes(nested: attr_name keyword, attr_value text)`, `files(nested: fileName keyword, content text)`, `authorLogin(keyword)`, `authorName(keyword)`, `creationDate(date, ignore_malformed)`, `description(text)`, `iteration(integer)`, `modificationDate(date, ignore_malformed)`, `revisionNote(text)`, `type(keyword)`, `version(keyword)`, `workflow(keyword)`, `tags(keyword 数组)`
- documents 追加：`docMId(text, id_analyzer)`, `folder(keyword)`, `title(text)`
- parts 追加：`partName(text)`, `partNumber(text, id_analyzer)`, `standardPart(boolean)`

> ⚠️ 旧文档臆造的 `partKey`/`docKey` 字段**在真 mapping 中不存在**。文档 ID 通过 docId（IterationKey 编码）作为 ES `_id`，不作为字段。

### 1.3 健康检查（IndexerManagerBean.ping:112）

| Java | Python 目标 | 状态 |
|------|------------|------|
| `ping()` → `esClient.execute(Health)` | `platform.py` health_check（现用 DB `SELECT 1`） | 可加 `es.ping()`，非必须 |

---

## 二、写入内容：EntityMapper（写入 ES 的 doc 唯一事实）

**Java 事实**（`EntityMapper` partIterationToJSON / documentIterationToJSON）——按 **PartIteration/DocumentIteration** 构建，不是 Revision。

### 2.1 part doc 字段（partIterationToJSON）

| ES 字段 | Java 来源 | Python ORM 来源（已核实 app/models/part.py） |
|---------|----------|---------------------------------------------|
| `workspaceId` | partIteration workspace | `pi.workspace_id` |
| `partNumber` | partMaster.number | `pi.revision.part_master.number` |
| `partName` | partMaster.name | `pi.revision.part_master.name` |
| `type` | partMaster.type | `pi.revision.part_master.type` |
| `version` | partRevision.version | `pi.revision.version` |
| `description` | partRevision.description | `pi.revision.description` |
| `iteration` | partIteration.iteration | `pi.iteration` |
| `standardPart` | partMaster.standardPart | `pi.revision.part_master.standard_part` |
| `creationDate` | partIteration.creationDate | `pi.creation_date` |
| `modificationDate` | partIteration.modificationDate | `pi.modification_date` |
| `revisionNote` | partIteration.iterationNote | `pi.iteration_note`（⚠️ PartIteration 无 revisionNote，Java 也是取 iterationNote 写入 revisionNote 字段——需读 EntityMapper 确认） |
| `authorLogin` | author.login | `pi.author_login` |
| `authorName` | author.name | ⚠️ ORM 无 author 关系的 name，需确认取值（可能 login） |
| `tags[]` | partRevision.tags | `pi.revision.tags`（label 列表） |
| `attributes[]` | instanceAttributes → {attr_name, attr_value} | `pi.instance_attributes`（需确认 ORM 关系名） |
| `files[]` | attachedFiles + 全文提取 → {fileName, content} | ⏸ 全文提取登记 REMINDERS，先只写 fileName |
| `workflow` | partRevision.workflow | `pi.revision.workflow_id` |

### 2.2 document doc 字段（documentIterationToJSON）

| ES 字段 | Java 来源 | Python ORM 来源（已核实 app/models/document.py） |
|---------|----------|--------------------------------------------------|
| `workspaceId` | docIteration workspace | `di.workspace_id` |
| `docMId` | documentMaster.id | `di.revision.documentmaster_id` |
| `title` | documentRevision.title | `di.revision.title` |
| `version` | documentRevision.version | `di.revision.version` |
| `type` | documentMaster.type | `di.revision.document_master.type` |
| `description` | documentRevision.description | `di.revision.description` |
| `iteration` | docIteration.iteration | `di.iteration` |
| `creationDate` | docIteration.creationDate | `di.creation_date` |
| `modificationDate` | docIteration.modificationDate | `di.modification_date` |
| `revisionNote` | docIteration.revisionNote | `di.revision_note`（✅ DocumentIteration 有 revision_note） |
| `folder` | documentRevision.location | `di.revision.location_completepath` |
| `authorLogin` | author.login | `di.author_login` |
| `authorName` | author.name | ⚠️ 同 part |
| `tags[]` | documentRevision.tags | 需确认 ORM 关系 |
| `attributes[]` | instanceAttributes | 需确认 ORM 关系 |
| `files[]` | attachedFiles + 全文提取 | ⏸ 同 part |
| `workflow` | documentRevision.workflow | `di.revision.workflow_id` |

> **实现前必做**：打开 `EntityMapper.java` 逐字段核对写入逻辑，再打开 Python ORM 核对属性名。ORM 关系名不确定的（attributes/tags/author.name）**先 grep 确认再写**。

---

## 三、docId 格式化（IndicesUtils.formatDocId:73）

**Java 事实**：ES 文档 `_id` = IterationKey.toString() 再经 `formatDocId`：
```java
// 行 73-80
return URLEncoder.encode(Tools.unAccent(id), "UTF-8").toLowerCase();
```
- PartIterationKey.toString() / DocumentIterationKey.toString() 决定原始 id 格式（需读 core 里的 Key 类确认，形如 `workspace/number/version/iteration`）
- 再 unaccent + urlencode + lowercase

| Java | Python 目标 | 复刻要点 |
|------|------------|---------|
| `formatDocId(iterationKey.toString())` | `_format_doc_id(key_str)` | 必须复刻 IterationKey 字符串格式 + 编码，否则 upsert/删除对不上同一 doc |

---

## 四、实时索引触发点（真实只有 6 处业务 + 2 处 workspace）

> ⚠️ 旧文档臆造 15 处（含 create/release/obsolete/setTags）。**Java 真源码只在下列位置触发索引**。create/release/markObsolete/setTags 在 Payara 中**不触发实时索引**（靠 admin reindex 补）。

| Java 调用点 | 操作 | Python 目标位置 |
|-------------|------|----------------|
| `ProductManagerBean.checkInPart:600` | `indexPartIteration(lastIteration)` | `product_manager.py checkin:403` 末尾 |
| `ProductManagerBean.deletePartRevision:2154` | 遍历 iteration `removePartIterationFromIndex` | `product_manager.py delete_revision:276` |
| `DocumentManagerBean.checkInDocument:1094` | `indexDocumentIteration(lastIteration)` | `document_manager.py checkin:493` 末尾 |
| `DocumentManagerBean.moveDocumentRevision:880` | 重索引 lastCheckedInIteration | `document_manager.py move_document:751` |
| `DocumentManagerBean.moveFolder:1178` | 批量重索引受影响文档 | `document_manager.py`（folder 移动，需确认对应方法） |
| `DocumentManagerBean.deleteDocumentRevision:1231` | 遍历 iteration `removeDocumentIterationFromIndex` | `document_manager.py delete_revision:103` |
| `WorkspaceManagerBean.createWorkspace:169` | `createWorkspaceIndex(ws)` | `workspaces.py create_workspace:502` 末尾（❌ 现缺） |
| `WorkspaceManagerBean.doDeleteWorkspace:111` | `deleteWorkspaceIndex(ws)` | `workspaces.py delete_workspace:603`（❌ 现缺）+ `admin.py delete_workspace:206` |

**索引方式**（`IndexerQueryBuilder.updateRequest:70/91`）：`doc_as_upsert=true` 的 Update 请求，不是普通 index。Python 用 `es.update(..., body={"doc": doc, "doc_as_upsert": True})` 复刻。

---

## 五、搜索（IndexerQueryBuilder + IndexerResultsMapper）

### 5.1 搜索流程

**Java 事实**（`IndexerManagerBean.searchPartRevisions:323` / `searchDocumentRevisions:301`）：
```
getSearchQueryBuilder(query) → BoolQuery.must(所有子查询)
→ indexManager.executeSearch(index, query, from, size)  [QUERY_THEN_FETCH]
→ indexerResultsMapper.processSearchResult(result, query)
   → 从 hits 提取 workspaceId/number(docMId)/version/iteration → IterationKey → 查 DB 恢复实体
```

| Java | Python 目标 | 复刻要点 |
|------|------------|---------|
| `searchPartRevisions(q, from, size)` | `es_query_builder.search_parts(ws, params)` → 返回 IterationKey 列表 → router 查 DB → PartRevisionDTO | 结果映射回 DB（ES 只存索引，DTO 从 DB 取） |
| `searchDocumentRevisions(q, from, size)` | `es_query_builder.search_documents(...)` 同上 | |
| `IndexerResultsMapper.extractValue:181`（值为 List 取 [0]） | key 提取时同样处理 | |
| `processSearchResult` + fetchHeadOnly | fetchHeadOnly 时仅保留 lastCheckedInIteration | 复刻 fetchHeadOnly 语义 |

### 5.2 查询字段构建（IndexerQueryBuilder.createCommonQueries:177 + createQueries）

**公共条件**（`createCommonQueries:177`，父类 SearchQuery 字段）：

| SearchQuery getter | REST 参数 | ES DSL（读 Java 确认精确 query 类型） |
|--------------------|-----------|--------------------------------------|
| `getQueryString()` | `q` | 全文 query（multi-field / query_string，读 Java 行 177+ 确认） |
| `getVersion()` | `version` | term/match on `version` |
| `getAuthor()` | `author` | on `authorLogin`/`authorName` |
| `getType()` | `type` | on `type` |
| `getCreationDateFrom/To()` | `createdFrom/To` | range on `creationDate` |
| `getModificationDateFrom/To()` | `modifiedFrom/To` | range on `modificationDate` |
| `getTags()` (String[]) | `tags` | terms on `tags` |
| `getContent()` | `content` | **nested** query on `files.content` |
| `getAttributes()` (AbstractAttributeQuery[]) | `attributes` | **nested** query on `attributes`（同名 should，不同名 must，见 `addAttributeToQueries:242`） |
| `isFetchHeadOnly()` | `fetchHeadOnly` | 结果映射阶段用 |

**Part 特有**（`createQueries(PartSearchQuery):158`）：

| getter | REST 参数 | ES DSL |
|--------|-----------|--------|
| `getPartNumber()` | `number` | on `partNumber`（id_analyzer） |
| `getName()` | `name` | on `partName` |
| `isStandardPart()` | `standardPart` | term on `standardPart` |

**Document 特有**（`createQueries(DocumentSearchQuery):134`）：

| getter | REST 参数 | ES DSL |
|--------|-----------|--------|
| `getDocMId()` | `id` | on `docMId`（id_analyzer） |
| `getTitle()` | `title` | on `title` |
| `getFolder()` | `folder` | on `folder` |

> **attributes 参数解析**：`SearchQueryParser.java` 把 `TYPE:name:value`（TEXT/NUMBER/BOOLEAN/URL/DATE/LOV）解析成 AbstractAttributeQuery。复刻搜索时需先复刻此解析格式。

### 5.3 REST 端点对照

| Java | Python 目标 | 复刻要点 |
|------|------------|---------|
| `GET /workspaces/{ws}/parts/search`（PartsResource:206，参数 q/number/name/version/author/type/created*/modified*/tags/content/attributes/from/size/fetchHeadOnly） | `parts.py search_parts:77`（现纯 DB LIKE） | 改 ES 优先 + DB fallback；补齐缺失参数 |
| `GET /workspaces/{ws}/documents/search`（DocumentsResource:115） | `documents.py search_documents:28`（现纯 DB LIKE） | 同上 |
| `PUT /admin/index/{ws}`（AdminResource:248，@RolesAllowed ADMIN） | `admin.py put_index:370`（现 stub） | 调 reindex；保持 ADMIN 鉴权 |
| `PUT /admin/index-all`（AdminResource:266，ADMIN） | admin.py（需新增或确认） | 遍历所有 workspace |
| `PUT /workspaces/{ws}/index`（WorkspaceResource:274，REGULAR+ADMIN） | workspaces.py reindex 端点（现 stub） | 调 reindex |

---

## 六、全量重建（IndexerManagerBean.doIndexWorkspaceData:359）

**Java 事实**：
```
checkAdmin(ws) → deleteIndices(ws) → createIndices(ws)
→ indexWorkspaceDocuments(ws): 按 BULK_SIZE=50 分页 documentMasterDAO.getPaginatedByWorkspace → addToBulk → sendBulk
→ indexWorkspaceParts(ws): 同上 partMasterDAO
→ 收集 BulkResult → sendBulkIndexationSuccess/Failure 邮件
```
- 异步（@Asynchronous），返回 202 Accepted
- BULK_SIZE=50（行 104）

| Java | Python 目标 | 复刻要点 |
|------|------------|---------|
| `indexWorkspaceData(ws)` | `indexer_manager.reindex_all(db, ws)` | 先删后建；**按 iteration 遍历**（不是 revision）；BULK_SIZE=50 分页；`elasticsearch.helpers.bulk` |
| `doIndexWorkspaceData`（分页 50） | 复刻分页 | 大 workspace 防 OOM |
| `indexAllWorkspacesData:339` | 遍历所有 workspace | admin 端点 |
| 邮件通知 | ⏸ 无 notifier，登记 REMINDERS | |
| @Asynchronous | FastAPI BackgroundTasks 或同步 | 决策见 design 文档 |

---

## 七、异常处理对照（方法论第 7 维：throw parity）

**Java throw**（IndexerManagerBean）：`WorkspaceAlreadyExistsException`（createWorkspaceIndex）、`AccountNotFoundException`（deleteWorkspaceIndex）、`IndexerRequestException`、`IndexerNotAvailableException`。

| Java throw | Python 处理 | 需 raise？ |
|-----------|------------|-----------|
| `WorkspaceAlreadyExistsException` | create_index exists 检查后幂等跳过 | ❌ ES 增强功能降级 |
| `AccountNotFoundException` | 无邮件通知，不查账户 | ❌ |
| `IndexerRequestException` | 索引失败静默日志；搜索失败 fallback DB | ❌ |
| `IndexerNotAvailableException` | 同上 | ❌ |

**决策**：ES 全文搜索为非核心增强，所有 ES 异常降级（静默日志 / DB fallback），Python 侧不新增 raise。审计第 7 维时对照本表确认即可。

---

## 八、Python 侧现状（迁移起点）

| 项 | 现状 | 需要做的 |
|----|------|---------|
| `requirements.txt` elasticsearch==6.8.2 | ✅ 已有 | — |
| `config.py` ES_URL | ✅ 已有 | 新增 `ES_INDEX_PREFIX="localhost"` |
| `app/services/indexer_manager.py` | ⚠️ 上一轮按**错误臆造**创建 | **重写**：索引名/mapping/iteration 粒度/docId 编码/upsert 全部对齐 Java |
| `app/services/es_query_builder.py` | ⚠️ 同上，字段错（partKey 等） | **重写**：字段对齐真 mapping，补齐全部搜索条件 |
| `parts.py search_parts:77` | 纯 DB LIKE | ES 优先 + DB fallback |
| `documents.py search_documents:28` | 纯 DB LIKE | 同上 |
| `admin.py put_index:370` | stub | 调 reindex_all |
| `workspaces.py create/delete_workspace` | ❌ 无 ES | 补建/删索引 |
| `product_manager.py checkin/delete_revision` | ❌ 无 ES | 补索引触发 |
| `document_manager.py checkin/delete/move` | ❌ 无 ES | 补索引触发 |
| `docs/file-mapping.md` | 已有 indexer/es_query 行 | 更新状态 |

> **重点**：`indexer_manager.py` / `es_query_builder.py` 已存在但内容基于错误臆造（`partKey`/`docKey`/`parts-{ws}` 命名/revision 粒度），**必须整体重写对齐 Java 事实**，不是增量修改。
