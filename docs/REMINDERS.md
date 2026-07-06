# Reminders

当前待办、已知问题、阻塞事项。**每次会话开始时检查本文件，收尾时更新。**

---

## 待办

### 高优先级

- [x] ~~throw matrix 补齐~~ — 51/55 ✅，throw-matrix.md 已对齐完成

- [ ] **PathData 域未实现**：PathDataMasterNotFoundException / PathToPathLinkNotFoundException / PathToPathLinkAlreadyExistsException / PathToPathCyclicException——pathdata CRUD 和 path-to-path link CRUD 都是 stub。实现后补 raise。

- [ ] **3D 预览不显示** — Nginx/uvicorn HTTP 代理层与 Three.js r90 交互差异。GLB 字节/headers 对齐，但全 FA 不加载。需 tcpdump 抓包或升级 Three.js。

- [ ] **装配同步（_sync_components）未完整迁移** — assembly BOM 同步部分仍在 Payara 处理。

### 中优先级

- [ ] **搜索为 DB 模糊匹配** — 无 Elasticsearch 全文搜索。不影响功能但性能随数据量下降。
  → **已完成 (2026-07-06)**: ES 全文搜索已迁移，迭代级索引 + ES 优先搜索 + DB fallback，172 测试通过。
- [ ] **reindex 邮件通知 i18n 中英双语** — notifier.py 已实现基础中英 i18n，后续需对齐 Java PropertiesLoader 完整多语言资源文件 + 账号语言字段填充。

- [ ] **Decimation 减面优化一直失败** — conversion 容器脚本缺失。

- [ ] **Windows 重启后 Docker 端口失效** — WSL mirrored 模式 timing 问题，`wsl --shutdown` 恢复。

- [ ] **portproxy 规则与 Docker 端口冲突** — iphlpsvc 占用 8000/8001。

### 低优先级

- [x] ~~QueryAlreadyExistsException~~ — query stub 已补重复名称校验 (2026-07-06)
- [x] ~~PasswordRecoveryRequestNotFoundException~~ — /auth/recover token 模式已补校验 + raise (2026-07-06)
- [x] ~~IndexerNotAvailableException / IndexerRequestException~~ — 不适用
- [x] ~~GCMAccountNotFoundException / GCMAccountAlreadyExistsException~~ — 不适用
- [x] ~~EffectivityNotFoundException / StorageException~~ — 全stub，throw-matrix标注不可实现

- [x] ~~ProductManagerBean.isCheckoutByAnotherUser NPE~~ — Payara 遗Bug

---

## 已知限制

- **CATIA 原生格式不支持转换** — `.CATPart`/`.CATProduct`/`.3dxml` 需预先导出为 STEP/STL
- **back 容器 JVM 参数需两次重启才生效**
- **Conversion service Decimation 持续失败** — 不影响 GLB 生成

---

## 已解决（近期）

- [x] **3项关键修复** — share密码绕过+document_files异常捕获+doc迭代instanceAttributes/linkedDocuments (2026-07-06)
- [x] **File/Doc/Folder/User异常类抛出对齐Payara** — binary_storage.py/document_manager.py/folders.py/user_manager.py 9处异常替换 (2026-07-06)
- [x] **Layer/Marker/Template/Part/Milestone/Platform异常对齐** — 10处异常替换 (2026-07-06)
- [x] **Products 6项关键修复** — decodePath -1前缀+替代件链接支持、_build_component 补充 substituteIds/notifications/attributes、6个stub端点基本实现、BOM端点新增、instance详情补充iteration、milestones语法修复 (2026-07-06)
- [x] **Share/安全关键修复** — entity-token 头 + 过期删除 + 公开共享逻辑 + password header + security entity token + exception 类 (2026-07-06)
- [x] **乐观锁 SELECT FOR UPDATE** — checkout/checkin/undo/update_iteration 添加行级锁，消除并发竞态窗口 (2026-07-06)
- [x] **文件映射+代码级对比方法论** — `docs/file-mapping.md` 52业务对+22基础设施对，5维度检查 (2026-07-06)
- [x] **迁移方法论确立** — 文件映射+6维代码级审计为唯一验收标准，路线图原始工作流顺序错误已修正 (2026-07-06)
- [x] **4轮全量审计清零 + 76项修复** — 60对→76问题→全修→0残留 (2026-07-06)
- [x] **144 passed, 0 failed** — 首次全绿（trace_file_service vault fixtures修复） (2026-07-06)
- [x] **3 轮全量审计清零** — 60对→35→11→14→0 问题 (2026-07-06)
- [x] **Router 22→32 拆分** — 每个 Python 文件 1:1 对应 Java Resource (2026-07-06)
- [x] **Service 10 个改名** — 对齐 Java Bean 命名 (2026-07-06)
- [x] **Stats 对齐 Payara** — COUNT PartRevision/DocumentRevision (2026-07-06)
- [x] **Stub 写操作修复** — enable/disable-user、front-options、publish/unpublish 等 15+ 端点从 stub 改为真实 DB 写入 (2026-07-06)
- [x] **全量尾斜杠补全** — 137 条 GET 路由 (2026-07-06)
- [x] **P5 工作流与权限** — 66 端点/6 功能域/完整迁移 (2026-07-05)
- [x] **系统化 Payara 对拍** — 133 端点 (2026-07-05)
- [x] **P4 变更管理** — Issue/Request/Order/Milestone (2026-07-05)
- [x] **P3 产品结构** — CI/Baseline/Configuration/Instance (2026-07-05)
- [x] **P2 文档与文件夹** — 80 测试通过 (2026-07-05)
- [x] **P1b 零件文件+转换回调** — 73 测试通过 (2026-07-05)
- [x] **P1a 零件核心 CRUD** — 57 测试通过 (2026-07-04)
- [x] **P0 FastAPI 基础设施** — JWT/Kafka/vault/DB (2026-07-04)
- [x] **转换服务 Python-only** — 2.7.0-py 镜像 (2026-07-04)
- [x] **deletePartRevision 4 项 EntityConstraint 补齐** (2026-07-06)
- [x] **test1 管理员权限修复** — workspace.admin_login = 'test1' (2026-07-06)
- [x] **stubs 消除：gen_id mask递增 + 逆链接实查 + download头补全 + home检测** — generate_id 真实DB查询+mask支持、aborted-workflows+4个inverse links实查、part_files download Last-Modified真实文件时间、folders home检测 (2026-07-06)
- [x] **products 域 5 项修复** — baselines 补字段、configs ACL 统一、searchCI 完整 DTO、cascade 真实实现、instance 字段名对齐 (2026-07-06)
- [x] **es_query_builder 审计修复（C5-C7, W11）** — q→query_string bool should、folder→match+fuzziness、移除 standardPart（2026-07-07）
- [x] **notifier/indexer_manager 审计修复** — notifier 重写对齐 Java INotifierLocal、indexer reindex_all 调用改为两个方法、bulk errors 提取修正 (2026-07-07)
- [x] **P2B 服务全量迁移 (30 文件)** — Configuration 域 PSFilterVisitor+5 filter+6 spec、Listeners 4 个、Products 3 个、Documents 2 个、Indexer 6 个（mapping/utils/client/mapper/extractor）、Validation 1 个（attributes_consistency_utils）、GCM 1 个（gcm_sender）。176 测试全绿。(2026-07-07)
- [x] **P3B-A Router 迁移 (8 端点文件)** — R-003 attributes.py（属性去重聚合）、R-016 lov.py（LOV CRUD）、R-022 effectivity.py 升级（真实 DB 写入+三种有效性类型）、R-033 tags.py（标签 CRUD+文档查询+创建文档打标签）、R-043 workspace_workflow（已在 workflow.py 集成）、R-045 document_template_files.py（multipart 上传+Range 下载）、R-047 part_template_files.py（multipart 上传+Range 下载）、R-014 FileResource（各子资源直接实现无需门面）。176 测试全绿。(2026-07-07)
