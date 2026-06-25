# Reminders

当前待办、已知问题、阻塞事项。**每次会话开始时检查本文件，收尾时更新。**

---

## 待办

### 高优先级

- [ ] **REST API 认证 401 问题未解决**
  `admin:password` 通过 BasicAuth 调用 REST API 始终返回 401，密码 hash 和 DB 匹配（MD5），账号 enabled=true，根因未排查清楚。
  目前绕过方案：直接 DB 操作。

- [ ] **MGM_VL01-57110/112/114-000_A 三个零件无 3D 预览**
  这三个零件 STEP 文件不含实体（运动学约束件），转换失败（`no geometry generated`）。后端已修复为 `succeed=true`，但当前 DB 中记录仍是 `succeed=false`（修复前产生的）。
  需要用户从前端重新上传 `.stp` 文件触发重新转换。

- [ ] **VL01-57110-000_A 装配结构树仍是旧数据（amount=0）**
  `sync.py` 的 `amount` bug 已修复，但当前 DB 里 VL01-57110-000_A 的 usage links 仍是修复前写入的 `amount=0`。
  需要用户用修复后的 CATIA Copilot 工具重新同步该装配体。

### 中优先级

- [ ] **Decimation 减面优化一直失败**
  每次转换都报 `Decimation failed with code = 1 read error`，是已知问题，不影响 GLB 生成，但值得排查。
  怀疑是 conversion 容器内 `/opt/decimater/openMeshDecimater.sh` 脚本缺失或损坏。

- [ ] **Windows 重启后 Docker 端口（8000/8001）有时在 Windows 侧不可访问**
  WSL mirrored 网络模式的已知 timing 问题。临时修复：`wsl --shutdown` 再重启 WSL。
  可考虑配置 Windows 启动任务自动处理，或加 portproxy 规则作为保底。

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

- [x] **`ConverterBean` race condition**：`handleConversionResultCallback` 用 `lastIteration()` 导致结果写错 iteration → 已修复为查 pending conversion 记录（2026-06-18）
- [x] **Workspace_2 历史 pending 记录**：20 条 `pending=true` 记录已清理（2026-06-18）
- [x] **后端 JVM 堆内存 OOM 风险**：2g → 4g（2026-06-18）
- [x] **空几何体转换报失败**：`no geometry generated` 改为标记 `succeed=true`（2026-06-22）
- [x] **装配结构 amount=0**：`sync.py _sync_node()` 补充 `"amount"` 字段（2026-06-22）
