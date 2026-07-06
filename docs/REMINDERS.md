# Reminders

当前待办、已知问题、阻塞事项。**每次会话开始时检查本文件，收尾时更新。**

---

## 待办

### 高优先级

- [ ] **3D 预览不显示** — Nginx/uvicorn HTTP 代理层与 Three.js r90 交互差异。GLB 字节/headers 对齐，但全 FA 不加载。需 tcpdump 抓包或升级 Three.js。

- [ ] **装配同步（_sync_components）未完整迁移** — assembly BOM 同步部分仍在 Payara 处理。

### 中优先级

- [ ] **搜索为 DB 模糊匹配** — 无 Elasticsearch 全文搜索。不影响功能但性能随数据量下降。

- [ ] **Decimation 减面优化一直失败** — conversion 容器脚本缺失。

- [ ] **Windows 重启后 Docker 端口失效** — WSL mirrored 模式 timing 问题，`wsl --shutdown` 恢复。

- [ ] **portproxy 规则与 Docker 端口冲突** — iphlpsvc 占用 8000/8001。

### 低优先级

- [ ] **`ProductManagerBean.isCheckoutByAnotherUser` NPE** — Payara 遗留 bug，不影响主要功能。

---

## 已知限制

- **CATIA 原生格式不支持转换** — `.CATPart`/`.CATProduct`/`.3dxml` 需预先导出为 STEP/STL
- **back 容器 JVM 参数需两次重启才生效**
- **Conversion service Decimation 持续失败** — 不影响 GLB 生成

---

## 已解决（近期）

- [x] **乐观锁 SELECT FOR UPDATE** — checkout/checkin/undo/update_iteration 添加行级锁，消除并发竞态窗口 (2026-07-06)
- [x] **文件映射+代码级对比方法论** — `docs/file-mapping.md` 52业务对+22基础设施对，5维度检查 (2026-07-06)
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
