# ES 搜索——Payara→Python 方法级详细映射

> 用于 ES 搜索实施的精确方法论参考。Java 方法签名源自 `IndexerManagerBean.java` (486 行)。

## 一、ES 索引生命周期管理

### 1.1 索引创建

**Java**: `public void createWorkspaceIndex(String workspaceId) throws WorkspaceAlreadyExistsException`
- 行 130。先 `indexManager.indicesExist(ws)` → 存在抛 `WorkspaceAlreadyExistsException` → `indexManager.createIndices(ws)` 创建 parts+documents 两个索引。
- 鉴权: `@RolesAllowed(ADMIN_ROLE_ID, REGULAR_USER_ROLE_ID)`
- 事务: `@TransactionAttribute(REQUIRES_NEW)`

**Python**: `def create_index(self, ws: str) -> None`
- 参数: `ws` 对应 `workspaceId`
- 逻辑: 遍历 `[(parts_prefix, PART_MAPPING), (docs_prefix, DOC_MAPPING)]`，`es.indices.exists()` → 不存在 `es.indices.create(index, body)`
- 返回值: None（无返回值，对齐 Java void）
- 异常: `try/except Exception → log warning`（Java 只捕获 IndexerNotAvailable/IndexerRequest）
- 状态: ✅

### 1.2 索引删除

**Java**: `public void deleteWorkspaceIndex(String workspaceId) throws AccountNotFoundException`
- 行 149。先 `accountManager.getMyAccount()`（获取当前用户→用于邮件通知）。`indexManager.deleteIndices(ws)`。失败时发邮件 `sendWorkspaceIndexationFailure`。
- 鉴权: `@RolesAllowed(ADMIN_ROLE_ID, REGULAR_USER_ROLE_ID)`

**Python**: `def delete_index(self, ws: str) -> None`
- 参数: `ws` 对应 `workspaceId`
- 逻辑: 遍历两个前缀，`es.indices.exists()` → `es.indices.delete()`
- 差异: 无邮件通知（Python 无 notifier 组件），无账户查询
- 状态: ✅

### 1.3 索引健康检查

**Java**: `public boolean ping()`
- 行 112。`esClient.execute(new Health.Builder().build())` → `result.isSucceeded()`

**Python**: 不单独实现，`platform.py` health_check 用 DB `SELECT 1` 替代
- 状态: ⚠️ 简化

---

## 二、实时索引（零件）

### 2.1 单零件索引

**Java**: `public void indexPartIteration(PartIteration partIteration)`
- 行 215。`indexerQueryBuilder.updateRequest(partIteration)` → `indexManager.executeUpdate(update)` → `DocumentResult`
- 异步: `@Asynchronous`（非阻塞）
- 鉴权: `@RolesAllowed(REGULAR_USER_ROLE_ID)`

**Python**: `def index_part_revision(self, pr: PartRevision) -> None`
- 参数: `pr` = PartRevision ORM 对象（Java 传 PartIteration，Python 升到 revision 级）
- 逻辑: `self._part_to_doc(pr)` → `es.index(index, _id, body)`
- 差异: 同步索引（无异步机制），按 revision 索引（Java 按 iteration）
- 索引文档 ID: `partKey`（`"NUMBER-VERSION"`）
- 状态: ⚠️（粒度不同）

### 2.2 批量零件索引

**Java**: `public void indexPartIterations(List<PartIteration> partIterations)`
- 行 240。过滤 `checkInDate != null` → `addToBulk(partIteration, bulk)` → `indexManager.sendBulk(bulk)`
- 异步: `@Asynchronous`

**Python**: reindex_all() 中内置，`elasticsearch.helpers.bulk(es, actions)`
- 差异: 不过滤 checkInDate（测试数据场景）
- 状态: ✅

### 2.3 零件从索引删除

**Java**: `public void removePartIterationFromIndex(PartIteration partIteration)`
- 行 279。`indicesUtils.getIndexName(ws, INDEX_PARTS)` → `indicesUtils.formatDocId(partIteration.getKey())` → `indexManager.executeRemove(indexName, docId)`
- 事务: `@TransactionAttribute(REQUIRES_NEW)`

**Python**: `def delete_part_revision(self, key: str, ws: str) -> None`
- 参数: `key` = `"NUMBER-VERSION"`（取代 PartIteration.getKey()） → `ws` = workspace_id
- 逻辑: `es.delete(index=parts-{ws}, id=key, ignore=[404])`
- 差异: `ignore=[404]`（ES 6.x API 风格，避免文档不存在的异常）
- 状态: ✅

---

## 三、实时索引（文档）

### 3.1 单文档索引

**Java**: `public void indexDocumentIteration(DocumentIteration documentIteration)`
- 行 168。`indexerQueryBuilder.updateRequest(documentIteration)` → `indexManager.executeUpdate`
- 异步: `@Asynchronous`

**Python**: `def index_document_revision(self, dr: DocumentRevision) -> None`
- 参数: `dr` = DocumentRevision ORM 对象
- 索引文档 ID: `docKey`（`"DOC_ID-VERSION"`）
- 状态: ⚠️（粒度不同）

### 3.2 批量文档索引

**Java**: `public void indexDocumentIterations(List<DocumentIteration> documentIterations)`
- 行 194。过滤 `checkInDate != null` → `addToBulk` → `sendBulk`

**Python**: reindex_all() 中内置
- 状态: ✅

### 3.3 文档从索引删除

**Java**: `public void removeDocumentIterationFromIndex(DocumentIteration documentIteration)`
- 行 262。`indicesUtils.getIndexName(ws, INDEX_DOCUMENTS)` → `formatDocId(docKey)` → `executeRemove`

**Python**: `def delete_document_revision(self, key: str, ws: str) -> None`
- 参数: `key` = `"DOC_ID-VERSION"`，`ws` = workspace_id
- 状态: ✅

---

## 四、ES 搜索

### 4.1 零件搜索

**Java**: `public List<PartRevision> searchPartRevisions(PartSearchQuery partSearchQuery, int from, int size)`
- 行 323。`indicesUtils.getIndexName(ws, INDEX_PARTS)` → `indexerQueryBuilder.getSearchQueryBuilder(partSearchQuery)` → `indexManager.executeSearch` → `indexerResultsMapper.processSearchResult`（ES doc → PartRevision 实体）
- 抛异常: `AccountNotFoundException, IndexerRequestException, IndexerNotAvailableException`

**Python**: `def search_parts(self, ws: str, params: dict) -> list[str]`
- 参数: `ws` 对应 `partSearchQuery.getWorkspaceId()`，`params` 对应 `PartSearchQuery` 各 getter
- 返回: `list[str]`（partKey 列表），调用方查 DB 补充完整 DTO
- 搜索构建: `es_query_builder.search_parts(ws, params)`
- 错误: ES 异常 → fallback DB LIKE
- 状态: ✅

**参数映射 (PartSearchQuery → Python dict)**:

| Java PartSearchQuery getter | Python params key | ES DSL | 说明 |
|---|---|---|---|
| `getWorkspaceId()` | `ws` 参数 | — | 索引选择 |
| `getQueryString()` | `"q"` | `multi_match` on partNumber^2 + partName + description | 全文搜索 |
| `getPartNumber()` | `"number"` | `match` on partNumber | 精确编号 |
| `getName()` | `"name"` | `match` on partName | 名称匹配 |
| `getVersion()` | `"version"` | `term` on version | 精确版本 |
| `getAuthor()` | `"author"` | `term` on authorLogin | 作者过滤 |
| `getType()` | `"type"` | — | 暂未索引 type 字段 |
| `getTags()` | `"tags"` | `terms` on tags | 标签数组 |
| `getContent()` | `"content"` | `match` on revisionNote | 全文搜索 |
| `getAttributes()` | `"attributes"` | `nested` query | 暂未实现 nested |
| `getCreatedFrom/To()` | `"createdFrom/To"` | `range` on creationDate | 日期范围 |
| `getModifiedFrom/To()` | `"modifiedFrom/To"` | `range` on modificationDate | 日期范围 |
| `isStandardPart()` | `"standardPart"` | `term` on standardPart | 布尔过滤 |
| — | `"from"/"size"` | ES `from`/`size` | 分页 |

### 4.2 文档搜索

**Java**: `public List<DocumentRevision> searchDocumentRevisions(DocumentSearchQuery, int from, int size)`
- 行 301。同零件搜索流程

**Python**: `def search_documents(self, ws: str, params: dict) -> list[str]`
- 状态: ✅

---

## 五、全量重建索引

### 5.1 工作区重建

**Java**: `public void indexWorkspaceData(String workspaceId)`
- 行 355。异步执行 `doIndexWorkspaceData(ws)`：
  1. `indexManager.deleteIndices(ws)` + `createIndices(ws)`（强制重建）
  2. `indexWorkspaceDocuments(ws)` → 按 BULK_SIZE=50 分页 `documentMasterDAO.getPaginatedByWorkspace`
  3. `indexWorkspaceParts(ws)` → 同上 `partMasterDAO.getPaginatedByWorkspace`
  4. 收集 `BulkResult` 错误，成功发邮件 `sendBulkIndexationSuccess`，失败发 `sendBulkIndexationFailure`
- 鉴权: `@RolesAllowed(ADMIN_ROLE_ID, REGULAR_USER_ROLE_ID)` + `userManager.checkAdmin(ws)`

**Python**: `def reindex_all(self, db: Session, ws: str) -> dict`
- 参数: `db`（SQLAlchemy Session，代 替 Java 的 DAO + JPA），`ws` 对应 `workspaceId`
- 逻辑:
  1. `delete_index(ws)` + `create_index(ws)`
  2. `db.query(PartRevision).filter(workspace_id=ws).all()` → `bulk(self.es, actions)`（不分页，一次性）
  3. `db.query(DocumentRevision).filter(workspace_id=ws).all()` → `bulk(self.es, actions)`
- 返回: `{"parts": N, "documents": M}`
- 差异: 不分页（Java BULK_SIZE=50），无邮件通知，同步执行（Java 异步）
- 状态: ⚠️（需加分页 + 异步）

### 5.2 全部工作区重建

**Java**: `public void indexAllWorkspacesData()`
- 行 339。`workspaceDAO.getAll()` → 逐个 `doIndexWorkspaceData(ws)`
- 鉴权: `@RolesAllowed(ADMIN_ROLE_ID)`

**Python**: 不单独实现，admin 逐 workspace 调 `reindex_all`
- 状态: ⚠️ 简化

---

## 六、索引触发点映射（CRUD→Index）

| Java 调用位置 (Bean.方法) | Python 调用位置 | 操作 |
|---|---|---|
| `ProductManagerBean.checkInPart:600` | `product_manager.py checkin()` 末尾 | `indexer.index_part_revision(pr)` |
| `ProductManagerBean.createPartMaster:275` | `product_manager.py create_part()` 末尾 | `indexer.index_part_revision(pr)` |
| `ProductManagerBean.updatePartIteration:895` | `product_manager.py update_iteration()` 末尾 | `indexer.index_part_revision(pr)` |
| `ProductManagerBean.releasePartRevision:1496` | `product_manager.py release()` 末尾 | `indexer.index_part_revision(pr)` |
| `ProductManagerBean.markPartRevisionAsObsolete:1519` | `product_manager.py mark_obsolete()` 末尾 | `indexer.index_part_revision(pr)` |
| `ProductManagerBean.deletePartRevision:2105` | `product_manager.py delete_revision()` 末尾 | `indexer.delete_part_revision(key, ws)` |
| `DocumentManagerBean.checkInDocument:1069` | `document_manager.py checkin()` 末尾 | `indexer.index_document_revision(dr)` |
| `DocumentManagerBean.createDocumentMaster:674` | `document_manager.py create_document()` 末尾 | `indexer.index_document_revision(dr)` |
| `DocumentManagerBean.saveTags:964` | `document_manager.py set_tags()` 末尾 | `indexer.index_document_revision(dr)` |
| `DocumentManagerBean.releaseDocumentRevision:1742` | `document_manager.py release()` 末尾 | `indexer.index_document_revision(dr)` |
| `DocumentManagerBean.deleteDocumentRevision:1187` | `document_manager.py delete_revision()` 末尾 | `indexer.delete_document_revision(key, ws)` |
| `WorkspaceManagerBean.createWorkspace:157` | `workspaces.py create_workspace()` 末尾 | `indexer.create_index(ws)` |
| `WorkspaceManagerBean.deleteWorkspace:103` | `workspaces.py delete_workspace()` 末尾 | `indexer.delete_index(ws)` |

---

## 七、关键差异总结

| 维度 | Java (IndexerManagerBean) | Python (indexer_manager.py) | 影响 |
|------|--------------------------|---------------------------|------|
| ES 客户端 | Jest (HTTP) | elasticsearch-py 6.8.2 | 无（接口等价） |
| 索引粒度 | 按 PartIteration/DocumentIteration | 按 PartRevision/DocumentRevision | 搜索结果一个 revision 一个 doc |
| 异步 | @Asynchronous（EJB 内置） | 同步 | reindex 阻塞请求 |
| checkInDate 过滤 | `getCheckInDate() != null` | 不过滤 | 索引包含未签入数据 |
| 邮件通知 | sendBulkIndexationSuccess/Failure | 无 | admin reindex 无反馈 |
| 分页重建 | BULK_SIZE=50 分页 | 一次性 bulk | 大型 workspace 可能 OOM |
| 事务 | REQUIRES_NEW 独立事务 | 无独立事务 | ES 失败不影响 DB CRUD |
