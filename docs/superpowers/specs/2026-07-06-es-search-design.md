# ES 全文搜索——设计文档

> **日期**：2026-07-06
> **目标**：完全复刻 Payara IndexerManagerBean 的实时索引 + ES 搜索，替代当前 DB LIKE 搜索。

## 1. 决策

| 决策点 | 选择 |
|--------|------|
| ES 版本 | 保持 6.6.1（不升级 Docker 容器） |
| Python client | elasticsearch==6.8.2（兼容 ES 6.6.1） |
| 索引策略 | 从 DB 全量重建（不复用 Payara 索引） |
| 实时索引范围 | 完全复刻 15 处 CRUD |
| 代码架构 | 单 indexer_manager.py + 各 CRUD 方法内联调用 |
| 异常策略 | ES 为非核心增强，所有 ES 异常降级（静默日志 / DB fallback），不新增 Python raise |
| ORM 字段来源 | 已核实 app/models/part.py & document.py（见 mapping 文档第八节），无 `last_iteration` 属性 |

## 2. 文件变更

### 新建

| 文件 | 用途 |
|------|------|
| `app/services/indexer_manager.py` | ES 连接、索引映射、文档 CRUD、批量 reindex |
| `app/services/es_query_builder.py` | 构建 ES bool query（对标 SearchQuery） |
| `tests/test_indexer_manager.py` | 单元测试 Mock ES |
| `tests/test_es_query_builder.py` | 单元测试 query DSL |

### 修改

| 文件 | 修改 |
|------|------|
| `app/services/product_manager.py` | 6 处 CRUD + index/delete ES |
| `app/services/document_manager.py` | 5 处 CRUD + index/delete ES |
| `app/routers/workspaces.py` | create/delete workspace → ES index |
| `app/routers/parts.py` | search_parts → ES 优先 + DB fallback |
| `app/routers/documents.py` | search_documents → ES 优先 + DB fallback |
| `app/routers/admin.py` | POST /admin/index/{ws} → ES reindex |
| `requirements.txt` | + elasticsearch==6.8.2 |
| `app/core/config.py` | + ES_URL |
| `docs/file-mapping.md` | + 2 对映射 |

## 3. ES 索引映射

**parts-{workspace_id}**: partNumber(分析文本), partName(文本), partKey(关键字), version(关键字), iteration(整数), description(文本), revisionNote(文本), authorLogin(关键字), authorName(关键字), creationDate(日期), modificationDate(日期), standardPart(布尔), workspaceId(关键字)

**documents-{workspace_id}**: docKey(关键字), docMasterId(关键字), title(文本), version(关键字), iteration(整数), description(文本), revisionNote(文本), authorLogin(关键字), authorName(关键字), creationDate(日期), modificationDate(日期), workspaceId(关键字)

## 4. 搜索 Query 构建

es_query_builder.py 逐字段映射 Payara SearchQuery 的每个参数到 ES DSL：q→multi_match, number→match, name→match, version→term, author→term, createdFrom/To→range, size→分页。

## 5. 实时索引触发点

**product_manager.py (6 处)**: checkin, update_iteration, release, mark_obsolete, delete_revision, create_part（各方法末尾 index_part_revision）

**document_manager.py (5 处)**: checkin, set_tags, create_document, release, delete_revision（各方法末尾 index_document_revision）

**workspaces.py (2 处)**: create_workspace → create_index, delete_workspace → delete_index

## 6. 错误处理

索引失败：try/except 静默记录日志，不 raise。搜索失败：ES 异常 → fallback DB LIKE。

## 7. Admin 重建

POST /admin/index/{ws} → delete_index → create_index → bulk_index → {"parts": N, "documents": M}

## 8. 测试

Mock ES 客户端，测索引 CRUD、query 构建、ES fallback。

## 9. 文件映射

| Java | Python |
|------|--------|
| IndexerManagerBean.java | indexer_manager.py |
| SearchQuery 系列 | es_query_builder.py |

## 10. Exception throw parity（方法论第 7 维）

IndexerManagerBean 抛出 4 类异常，本特性全部降级处理，**Python 侧不新增 raise**。逐条决策见 `plans/2026-07-06-es-search-mapping.md` 第九节。

| Java throw | Python 处理 | 需 raise |
|-----------|------------|---------|
| WorkspaceAlreadyExistsException | exists 检查后幂等跳过 | ❌ |
| AccountNotFoundException | 无邮件通知，不查账户 | ❌ |
| IndexerRequestException | 静默日志 / DB fallback | ❌ |
| IndexerNotAvailableException | 静默日志 / DB fallback | ❌ |

## 11. 已知差异登记（对齐完成前须确认，非遗漏）

以下差异是**有意为之的设计取舍**，非未完成项。审计时确认存在即可，无需补齐：

| # | 差异 | Java | Python | 决策理由 |
|---|------|------|--------|---------|
| 1 | 索引粒度 | 按 Iteration | 按 Revision | 搜索结果一 revision 一 doc，前端够用 |
| 2 | 异步 | @Asynchronous | 同步 | reindex 阻塞请求，可接受（admin 手动触发） |
| 3 | checkInDate 过滤 | 过滤未签入 | 不过滤 | 测试数据场景 |
| 4 | 邮件通知 | 有 | 无 | Python 无 notifier 组件 |
| 5 | 分页重建 | BULK_SIZE=50 | 一次性 bulk | 当前 workspace 规模小；大 workspace 风险已登记 REMINDERS |
| 6 | revisionNote(Part) | PartIteration.revisionNote | 用 iteration_note 代 | Python PartIteration 无 revision_note 字段 |

## 12. 对齐完成标准（硬性条件，缺一不可）

对标 `docs/migration-methodology.md` 第五节，本特性收敛标准：

| # | 条件 | 验证方法 |
|---|------|---------|
| 1 | indexer_manager.py 所有方法 import + 方法级冒烟通过 | Task 2 Step 2 冒烟脚本输出 `OK` |
| 2 | ORM 字段引用全部命中真实属性 | 对照 mapping 文档第八节，冒烟脚本不抛 AttributeError |
| 3 | throw parity 全部登记 | 对照本文档第 10 节，无遗漏 raise |
| 4 | 15 处实时索引触发点全部插桩 | 对照 mapping 文档第六节逐行 ✅ |
| 5 | 搜索 ES 优先 + DB fallback 双路径可用 | 断开 ES 后 pytest 搜索用例仍 PASS |
| 6 | 已知差异全部登记（非遗漏） | 对照本文档第 11 节 |
| 7 | 全量测试通过 | `pytest tests/ -q` 144+ passed |
| 8 | file-mapping.md 增补 2 对映射 | Task 9 Step 3 完成 |
