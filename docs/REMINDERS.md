# Reminders

当前待办、已知问题、阻塞事项。**每次会话开始时检查本文件，收尾时更新。**

---

## 待办

> 📋 **后端迁移剩余缺口不在此列**——完整台账见 `docs/migration/loose-ends.md`。2026-07-10 已完成 PathData/P2P 域 + 全量对比修复 + 用户姓名/权限修复合集，并**新增 Query 自定义查询执行引擎 + Importer 属性导入域（分支 feat/py-query-execution-engine）**。**剩余功能域**：① WebSocket /ws 403 修复；② 种子脚本修复（解阻 10 个 pytest 失败）。本文件只保留**跨领域非迁移**待办。

### 高优先级

- [x] **Workflow role_mapping 结构性修复 (2026-07-07)** — 多对多表已接入
- [ ] **3D 预览不显示** — Three.js r90 交互差异，需升级或抓包
- [x] **3D 预览三根因修复（2026-07-11）** — instances stub / geometryFileURI 逗号拼接 / CADFileView OBJ→GLB，已部署验证 GD50_Frame-A instances 正确返回 + Product1-A 9 子组件递归遍历
- [x] **update_iteration 3 项辅助功能已补齐 (2026-07-07)**

### 中优先级

- [ ] **reindex 邮件通知 i18n** — 基础实现已完成，待补全多语言资源
- [x] **Decimation 减面优化（2026-07-11 以 LOD 生成替代）** — conversion-service-py 已内置三级 LOD（deflection 0.05/0.30/1.00），失败降级
- [ ] **Windows 重启后 Docker 端口失效** — `wsl --shutdown` 恢复
- [x] **WebSocket /ws 403（2026-07-10 已修复）** — 路由路径对齐 `/docdoku-plm-server-rest/ws` + 补 `WebSocket` 类型注解，握手 101 + AUTH_OK
- [x] **Conversion Service Python 化收尾（2026-07-11）** — conversion-service-py 完整接管：docker-compose.yml 本地 build、LOD 三级精度（deflection 0.05/0.30/1.00）失败降级、旧 Java 目录标注废弃。容器已重建部署，Kafka 连接正常。

---

## 用户报出的 Bug（2026-07-10 更新）

| # | 问题 | 状态 | 备注 |
|---|------|------|------|
| 1 | ~~删除工作区"未找到用户 test1"~~ | ✅ Fixed | deps.py 补 admin_login + usergroup_user 组检查 |
| 2 | ~~创建基线 TypeError + 校验缺失~~ | ✅ Fixed | BFS 校验 + response 补 author |
| 3 | 通知设置不持久化 | ⏳ 待确认 | API 实现正确，可能是前端权限问题 |
| 4 | Payara JPA 缓存 8000/8005 权限互相不可见 | ⏳ 已知 | EclipseLink L2 缓存架构问题 |
| 5 | ~~effectivities 500~~ | ✅ Fixed | pre.workspace_id→pre.partmaster_workspace_id |
| 6 | ~~用户列表显示 login 而非姓名~~ | ✅ Fixed | tasks/doc_baselines/product_structure 全量补 Account.name |
| 7 | ~~零件创建 422 (camelCase)~~ | ✅ Fixed | PartCreationDTO 补 Field alias |
| 8 | ~~零件列表"显示全部" 422~~ | ✅ Fixed | length ge=1→ge=0 对齐 Payara pMaxResults==0 |
| 9 | ~~admin 账号前端崩溃 (CoWorkersAccessView)~~ | ✅ 已定位 | 前端 bug（4 个 main.js 缺 admin guard），非后端 |
| 10 | ~~export-files 3 端点 500~~ | ✅ Fixed | br.fullname/pi.nativecadfile_fullname/bd.target_docrevision_version |
| 11 | ~~LOV 500~~ | ✅ Fixed | listofvalues→lov 表名修正 |
| 12 | ~~groups 创建 500~~ | ✅ Fixed | create_group 补 db.flush() |

---

## 已知限制

- **CATIA 原生格式不支持转换** — 需预先导出 STEP/STL
- **back 容器 JVM 参数需两次重启** — Payara 特性
- **Conversion service Decimation 持续失败** — 不影响 GLB 生成
- **pytest 10 failures** — 种子数据脚本权限问题导致（非代码 bug）

---

## 已解决（近期）

- [x] **2026-07-11 删除工作区遗漏 binaryresource + vault 文件修复（back-py）**:
  - 症状：删 GD50 工作区→重建→上传附件报 409 `文件已存在`
  - 根因：`delete_workspace` 只按 workspace_id 级联删 DB，遗漏 ① `binaryresource` 表（无 workspace_id 列，主键 fullname，残留 102 行）② vault 磁盘文件夹（从不删）；`save_attached` 查 BinaryResource DB 记录判重 → 409
  - Payara 比对：`deleteWorkspace` = removeWorkspace（BinaryResource 靠 PartIteration JPA orphanRemoval 级联）+ `deleteWorkspaceFolder`(FileUtils.deleteDirectory) + 删 ES 索引；Payara 该操作 `@Asynchronous`
  - 修复 A：级联末尾 `DELETE FROM binaryresource WHERE fullname LIKE '{ws}/%' ESCAPE '\'`（转义对齐 WorkspaceDAO.java:130）
  - 修复 B：commit 后 `shutil.rmtree(VAULT_PATH/ws)`，失败仅记日志（Python 端保持同步）
  - docker cp 部署 back-py + 重启；存量 GD50 用修复后 delete 重删即清净

- [x] **2026-07-11 零件迭代更新 500（实例属性 FK 冲突）修复（back-py）**:
  - 症状：CATIA Copilot 同步更新零件 `PUT .../parts/{pn}-{ver}/iterations/{n}` 报 500 `ForeignKeyViolation fk_partiteration_attribute_instanceattribute_id`
  - 根因：checkout 创建新迭代时实例属性浅拷贝（新迭代复用旧迭代同一 instanceattribute 行），更新时删该行触发 FK 冲突（另一迭代仍引用）
  - 已与 Payara Java 逐条比对确认：Java `checkOutPart` 对每属性 `clone()+persist` 深拷贝独占，更新靠 orphanRemoval 删本迭代行
  - 修复 A（`_copy_iteration_files`）：检出复制实例属性改深克隆（INSERT...SELECT...RETURNING 新 id）
  - 修复 B（`_sync_instance_attributes`）：删孤儿前查是否被其它 partiteration_attribute 引用，共享则跳过，兜底 + 修复存量坏数据（更新后自愈）
  - docker cp 部署 back-py + 重启

- [x] **2026-07-11 SQL 列名/表名批量修复 + DTO 缺字段修复（back-py）**:
  - 修复 `validate_sql_columns.py` 报的 34 处 raw SQL 错误（14 文件）：attributes/document/product_instances/products/tasks/cascade_action/instance_body_writer/notification/subscription/part_notification/organization/product_manager/part_workflow/webhook；均先经 information_schema 核实真实列名/表名
  - 修复 3 个 CRITICAL DTO 缺字段（ConversionResultDTO.partIterationKey / UserDTO.membership / WorkspaceWorkflowCreationDTO.workflow），消除 422
  - docker cp 部署 back-py + 重启，启动无导入错误
  - ⚠️ 遗留：validate_sql_columns.py 3 处 `UPDATE SET` 误报（正则误匹配 `ON CONFLICT DO UPDATE SET`）+ 14 处自增 id NOT NULL 误报，建议后续改进脚本正则
  - ⚠️ validate_dto_fields.py 2 处 CRITICAL（PathDataIterationCreationDTO.partLinksList / ProductBaselineCreationDTO.author）为脚本把请求 CreationDTO 误映射到响应 DTO，缺字段属响应侧，非真实 422，未处理


- [x] **2026-07-10 工作区删除 500 + WebSocket 403 修复**（分支 feat/py-query-execution-engine）:
  - 删除工作区：手写级联补全（对齐 WorkspaceDAO.removeWorkspace，replica 模式关 FK 触发器），保留 account/credential/usergroupmapping，仅删 userdata；对 Workspace_2 真实数据非破坏性验证残留引用全 0
  - WebSocket：路由路径 `/docdoku-plm-server-rest/ws` + 补 `WebSocket` 注解（原 FastAPI 误判 websocket 为必填 query 参数），握手 101 + AUTH_OK
  - 注：`test_query_save` 因用户删除"测试工作区"导致其硬编码依赖（userdata e@测试用工作区）缺失而失败——数据/测试脆弱性，非代码回归；归入种子脚本待办

- [x] **2026-07-10 Importer 属性导入域**（分支 feat/py-query-execution-engine）:
  - Excel 解析器（对齐 ExcelParser.java）+ 属性合并工具（merge/LOV）+ Import 记录 CRUD
  - ImporterService 属性导入编排（checkout→dtype 写入→checkin，错误门控）+ dry-run 预览
  - 5 个 REST 端点接入 `/workspaces/{ws}/parts/...`；仅 .xlsx 属性导入（BOM 保留 stub）
  - 最终评审 3 项 MUST-FIX 修复（列名白名单防注入 / response_model / 记录顺序）
  - pytest 272 passed（+83）；docker cp 部署 + 线上冒烟全链路通过
  - ⚠️ 设计分歧：`_write_iteration_attributes` 写 dtype，`_sync_instance_attributes` 不写（详见 loose-ends 二）

- [x] **2026-07-10 Query 执行引擎**（分支 feat/py-query-execution-engine）:
  - 查询保存（递归 queryrule 树）+ PartRevision 执行器（前缀路由/operator/属性 EXISTS）
  - PathData 执行器（pd-attr-\*）+ context PBS 过滤 + mergeRows + QueryResult 序列化
  - runCustomQuery 端点（run/save/export）；pytest 189 passed（+22）；docker cp 部署 + 线上冒烟通过

- [x] **2026-07-10 全量修复合集**（67 文件，c668d31）:
  - PathData/P2P 域完整实现（18 端点 + Service + DFS 环检测）
  - 全量对比修复：export-files SQL 列名、LOV 表名、effectivities 列名、groups FK、parts length=0
  - 用户姓名全量修复：tasks/doc_baselines/product_structure/products
  - 权限 bug + deps 访问控制对齐 + PartCreationDTO camelCase
  - baseline 完整修复（校验 + 响应 + parts 端点）
  - 4 个 FA 自创端点删除
  - 对比脚本增强（158 端点 + 错误文本对比 + 行为测试）
  - 176 passed / 1 skipped / 行为测试 10/10

- [x] **审计遗留三项处理 (2026-07-08)**:
  - check_write_access null-ACL 全覆盖
  - extra=forbid 静默 500 — 7 项风险修复
  - 176 passed / 1 skipped，线上 5 端点 200/204 无 500

- [x] **审计修复 B1-B7 全量完成 (2026-07-07)** — 12/13 发现已修复（见 audit-report.md）:
  B1: 级联删除 8 表 + 模板 + Workflow Tasks
  B2: ACL 写权限 + 组成员校验 + 签出保护 + InstanceAttributeTemplates
  B3: 39 NotFound→404 + 补全 2 路由
  B4: 文档/零件/变更 DTO 字段补全
  B5: Workflow admin绕过 + SequentialActivity + status移除
  B6: 7 个 raise 补齐（NotAllowed42 + AccessRight × 5 + mask）
  B7: 6 实现 + 12 STUB 标注 + 6 TODO 清理 → 0 TODO 残留
  176 passed, 1 skipped — 全程零回归

- [x] **P4B WebSocket + Extension 全量迁移 (2026-07-07)** — WS /ws 端点 + Chat/Collaborative/Status/WebRTC 模块 + EXT converters/importers DTO

- [x] **P3B Router + Export 迁移 (2026-07-07)** — P3B-A (8 端点) + P3B-B (15 文件 utility/导出)

- [x] **P2B 服务全量迁移 (2026-07-07)** — Configuration 域 + Listeners + Products + Documents + Indexer + Validation + GCM

- [x] **CSV tracker 524/524 清零 (2026-07-07)**

- [x] **Elasticsearch 全文搜索 (2026-07-06)** — 9 个 service 文件（索引管理/查询/映射/提取），ES 优先搜索 + DB fallback

- [x] **文档审计体系搭建 (2026-07-07)** — DOCS_INDEX.md + 归档 17 个过时 superpowers 文件

- [x] **throw-matrix 补齐 + i18n by pass 审计** — 51/55 throw matrix 对齐
