# Reminders

当前待办、已知问题、阻塞事项。**每次会话开始时检查本文件，收尾时更新。**

---

## 待办

> 📋 **后端迁移剩余缺口不在此列**——完整台账见 `docs/migration/loose-ends.md`。2026-07-10 已完成 PathData/P2P 域 + 全量对比修复 + 用户姓名/权限/Baseline/LOV/export-files SQL 修复合集。**剩余 2 个功能域**：① Importer 导入 ② Query 执行引擎。本文件只保留**跨领域非迁移**待办。

### 高优先级

- [x] **Workflow role_mapping 结构性修复 (2026-07-07)** — 多对多表已接入
- [ ] **3D 预览不显示** — Three.js r90 交互差异，需升级或抓包
- [x] **update_iteration 3 项辅助功能已补齐 (2026-07-07)**

### 中优先级

- [ ] **reindex 邮件通知 i18n** — 基础实现已完成，待补全多语言资源
- [ ] **Decimation 减面优化** — conversion 容器脚本缺失
- [ ] **Windows 重启后 Docker 端口失效** — `wsl --shutdown` 恢复
- [ ] **WebSocket /ws 403** — 握手失败，已知遗留

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
