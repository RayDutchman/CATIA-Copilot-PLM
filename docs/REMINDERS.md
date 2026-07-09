# Reminders

当前待办、已知问题、阻塞事项。**每次会话开始时检查本文件，收尾时更新。**

---

## 待办

> 📋 **后端迁移剩余缺口不在此列**——完整台账见 `docs/migration/loose-ends.md`（~59 处，含 PathData/装配路径、Importer、产品配置降级、OnDemandConverter、WorkspaceManager stub 等）。本文件只保留**跨领域非迁移**待办。

### 高优先级

- [x] **Workflow role_mapping 结构性修复 (2026-07-07)** — TASK_USER/TASK_USERGROUP 多对多表已接入: instantiate_workflow INSERT 分配, _is_potential_worker 查双表, get_assigned_tasks JOIN 双表。对齐 Java Task.assignedUsers/assignedGroups。

- [ ] **3D 预览不显示** — Nginx/uvicorn HTTP 代理层与 Three.js r90 交互差异。GLB 字节/headers 对齐，但 FA 侧不加载。需 tcpdump 抓包或升级 Three.js。

- [x] **update_iteration 3 项辅助功能已补齐 (2026-07-07)**:
  - `_sync_instance_attribute_templates` — InstanceAttributeTemplate 同步
  - `hasValidChange` 校验 — AttributesConsistencyUtils 验证
  - ES reindex — indexer_manager.index_part_revision
  **装配 BOM 同步组件（_sync_components）本身已完整实现**（DELETE old + INSERT PartUsageLink + CADInstance + BFS 循环检测）

### 中优先级

- [ ] **reindex 邮件通知 i18n 中英双语** — notifier.py 已实现基础中英 i18n，后续需对齐 Java PropertiesLoader 完整多语言资源文件 + 账号语言字段填充。

- [ ] **Decimation 减面优化一直失败** — conversion 容器脚本缺失。

- [ ] **Windows 重启后 Docker 端口失效** — WSL mirrored 模式 timing 问题，`wsl --shutdown` 恢复。

- [ ] **portproxy 规则与 Docker 端口冲突** — iphlpsvc 占用 8000/8001。

---

## 已知限制

- **CATIA 原生格式不支持转换** — `.CATPart`/`.CATProduct`/`.3dxml` 需预先导出为 STEP/STL
- **back 容器 JVM 参数需两次重启才生效**
- **Conversion service Decimation 持续失败** — 不影响 GLB 生成
- **REST API BasicAuth 401** — `admin:password` 经 BasicAuth 调 REST API 返回 401（JWT 正常）

---

## 已解决（近期）

- [x] **审计遗留三项处理 (2026-07-08)**:
  - **check_write_access null-ACL 全覆盖** — 补全 7 处未传 workspace_id 的调用点（milestones/change_common/document_manager×3/workflow_manager 封装+2 caller/change_manager 一致性），acl_id=None 时正确校验 workspace 写权限
  - **extra=forbid 静默 500** — 7 项风险修复，全部对齐 Payara Java DTO：TaskDTO 删 closingDate；ACLDTO 改 List<ACLEntryDTO>+2 Map；WorkflowModelDTO workspaceId→reference；TaskHolderDoc 端点改 DocumentRevisionDTO（light）；ProductInstance 删 productBaselineId/workspaceId；OrganizationDTO 补 owner
  - **_relaunch_workflow** — 验证审计遗留已于 2164b07/9bfe150 解决（INSERT SELECT 深拷贝），无需改动
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
