# Reminders

当前待办、已知问题、阻塞事项。**每次会话开始时检查本文件，收尾时更新。**

---

## 待办

### 高优先级

- [ ] **3D 预览不显示（已定位，待修复）**
  零件数据+GLB文件均由 FastAPI 提供时，Three.js r90 不加载 GLB。已确认 GLB 文件有效、
  geometryFileURI 正确、CORS 头正常、字节与 Payara 完全一致。
  隔离测试 parts→FA+files→Payara 时 3D 正常，全 FA 时不正常。
  推测为 Nginx/uvicorn HTTP 代理层行为差异 (chunked传输/keepalive/buffer flush) 与
  Three.js r90 XHR 加载交互问题。需 tcpdump 抓包或升级 Three.js 版本解决。

- [ ] **JWT 过期风险提醒**：上传 nativecad 时将当前请求 token 透传给 Kafka 消息 userToken，转换服务用此 token 回调。若 token 在转换完成前过期（默认 3h），转换服务回调会 401 失败。建议后续改为服务间 token（如生成长期 API key 或在 conversion_service 内置白名单）。

### 中优先级

- [ ] **P5 工作流与权限**：Task 1-6 已完成（ORM 4 模型 + ACL/Security/Role/UserMgmt/Account/Notification 路由），待 Task 7+（Workflow 路由 + Webhook 路由 + 测试）。

- [ ] **装配同步仍走 Payara**：P1b 仅做零件单体 CRUD，装配 BOM 同步（update_iteration 含 _sync_components）仍在 Payara 处理。迁移到 FastAPI 待 P5+。

- [ ] **搜索为 DB LIKE MVP**：当前用 `ilike` 模糊匹配，无 Elasticsearch 全文搜索。功能正常但随数据量增长性能下降。后续 P5+ 独立子项目。

- [ ] **REST API 认证 401 问题未解决**
  `admin:password` 通过 BasicAuth 调用 REST API 始终返回 401，密码 hash 和 DB 匹配（MD5），账号 enabled=true，根因未排查清楚。
  目前绕过方案：直接 DB 操作。

- [ ] **MGM_VL01-57110/112/114-000_A 三个零件无 3D 预览**
  这三个零件 STEP 文件不含实体（运动学约束件），转换失败（`no geometry generated`）。后端已修复为 `succeed=true`，但当前 DB 中记录仍是 `succeed=false`（修复前产生的）。
  需要用户从前端重新上传 `.stp` 文件触发重新转换。

- [ ] **VL01-57110-000_A 装配结构树仍是旧数据（amount=0）**
  `sync.py` 的 `amount` bug 已修复，但当前 DB 里 VL01-57110-000_A 的 usage links 仍是修复前写入的 `amount=0`。
  需要用户用修复后的 CATIA Copilot 工具重新同步该装配体。

- [ ] **Decimation 减面优化一直失败**
  每次转换都报 `Decimation failed with code = 1 read error`，是已知问题，不影响 GLB 生成，但值得排查。
  怀疑是 conversion 容器内 `/opt/decimater/openMeshDecimater.sh` 脚本缺失或损坏。

- [ ] **Windows 重启后 Docker 端口（8000/8001）有时在 Windows 侧不可访问**
  WSL mirrored 网络模式的已知 timing 问题。临时修复：`wsl --shutdown` 再重启 WSL。

- [ ] **portproxy 规则与 Docker 端口冲突（2026-06-25 发现）**
  Windows 的 `portproxy` 规则（`0.0.0.0:8000/8001 → 127.0.0.1:8000/8001`）由 `iphlpsvc` 持续监听，
  重启后仍存在，导致 Docker 无法绑定端口，front/back 容器卡在 `Created` 状态。
  **修复方法**：
  ```powershell
  netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=8000
  netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=8001
  ```
  然后 `docker compose up -d --force-recreate front back`。
  WSL mirrored 模式下这两条 portproxy 本来就是多余的，**不要再添加**。

### 低优先级

- [ ] **`ProductManagerBean.isCheckoutByAnotherUser` NPE（第 3623 行）**
  多次出现 NullPointerException，触发点在 `getPartRevision()` 调用链。目前不影响主要功能，但值得修复。

---

## 已知限制

- **CATIA 原生格式不支持转换**：`.CATPart`、`.CATProduct`、`.3dxml` 无法直接转换，需在 CATIA 中预先导出为 STEP/STL
- **back 容器 JVM 参数需两次重启才生效**：Payara asadmin 修改 JVM options 后，第一次重启写入 domain.xml，第二次才以新参数启动
- **Conversion service Decimation 持续失败**：已知问题，不影响 GLB 生成

---

## 已解决（近期）

- [x] **P4 变更管理**：ChangeIssue/Request/Order/Milestone 完整实现 + Nginx 路由切换 + Payara 对拍通过（2026-07-05）
- [x] **P3 产品结构**：ConfigurationItem/Baseline/Configuration/Instance + ComponentDTO 递归 + decodePath + Nginx 2 路由块切换（2026-07-05）
- [x] **对齐债务 — P3/P4 跨模块约束补齐**：deletePartRevision 4 项约束（配置项根/基线/替代品/变更项）已全部实现（2026-07-05）
- [x] **P2 文档与文件夹+模板**：80 测试通过，Nginx 4 路由块已切，Payara 对拍通过（2026-07-05）
- [x] **系统化 Payara 对拍**：零件+文档 全部端点对拍+修复——路由顺序补5处、缺失端点补9处、字段差异修复（2026-07-05）
- [x] **尾斜杠 307 修复**：parts/documents/nativecad/attachedfiles/doc-upload 加双路由（2026-07-05）
- [x] **P1b 零件文件+转换回调+状态+搜索**：73 测试通过，Payara back 已退出零件功能（2026-07-05）
- [x] **P1a 零件核心 CRUD + 行为对齐**：57 测试通过，14 端点 + i18n 基础设施 + 异常体系（2026-07-04）
- [x] **P0 FastAPI 后端基础设施**：17 测试通过，JWT/Kafka/vault/DB 全部就绪（2026-07-04）
- [x] **转换服务迁移为 Python-only**：`2.7.0-py` 镜像上线，aiokafka 手动 commit（2026-07-04）
- [x] **vault 路径空格转下划线碰撞**：`Tools.unAccent()` 修复（2026-07-04）
- [x] **`ConverterBean` race condition**：查 pending conversion 记录（2026-06-18）
- [x] **空几何体转换报失败**：`no geometry generated` → `succeed=true`（2026-06-22）
- [x] **装配结构 amount=0**：`sync.py` 补充 `"amount"` 字段（2026-06-22）
