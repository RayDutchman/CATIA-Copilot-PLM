# Reminders

当前待办、已知问题、阻塞事项。**每次会话开始时检查本文件，收尾时更新。**

---

## 待办

### 高优先级

- [ ] **P1b：零件文件 + 转换回调 + 状态管理（下一阶段，待规划）**
  P1a-core（CRUD）与 P1a-align（行为对齐批次 0-2）均已完成。下一阶段 P1b：
  nativecad 上传下载 + 附件 + 转换回调 + release/obsolete/tags + 搜索。
  规划时**必须遵循标准每阶段工作流**（见 `docs/superpowers/fastapi-migration-roadmap.md`）：
  ORM→端点(用 i18n 异常)→对齐审计→Payara 对拍→前端实测→**通过后才切 Nginx**。
  待细化的 i18n 校验点：
  - saveNativeCADInPartIteration/saveFileInPartIteration：NotAllowedException4 + CAD 白名单
  - handleConversionResultCallback：findPendingConversionForRevision 定位 + 空几何跳过
  - createPartRevision：NotAllowedException40/41/56
  - releasePartRevision：NotAllowedException46/41/38
  - markPartRevisionAsObsolete：NotAllowedException36
  - removeFileInPartIteration、标签管理
  P1b 完成后 Payara back 容器可退出零件相关功能。

- [ ] **对齐债务（跨模块约束/字段，待属主阶段补齐）**
  详见路线图"对齐债务追踪"表。摘要：
  - deletePartRevision 3 约束（配置项根/基线→P3，变更项→P4，替代品→P1b/P3），已打 TODO
  - PartRevisionDTO.notifications 始终空（→P5，需 ModificationNotification 表）

- [ ] **转换服务当前是"混合镜像"临时方案，待迁移为 Python-only**
  ~~重建的 Java runner jar 有 SmallRye 间歇性"消费但不投递"故障。当前生产用混合镜像（旧 runner jar + 新 lib jar）勉强可用。
  完整迁移方案见 `docs/architecture/conversion-service-python-migration-plan.md`（待评审，~5 人天）。
  **回滚资产**：镜像 tag `docdoku-plm-conversion-service:2.6.2-jvm-hybrid-rollback` + `docdoku-plm-conversion-service/rollback-artifacts/app.jar.hybrid-rollback`。
  遗留：Inner Plate 2010 / Pinion 2010 / Thrust Washer 三个件转换失败（旧 unAccent 阻塞 + JWT 叠加），需重新上传。~~
  **已完成（2026-07-04）**：迁移为 Python-only（`2.7.0-py`），回归验证通过。
  回滚方式：`docker-compose.yml` 中 `image:` 改为 `2.6.2-jvm-hybrid-rollback` 一行即可。
  遗留：Inner Plate 2010 / Pinion 2010 / Thrust Washer 需重新上传（旧 token 已失效）。

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
- [x] **项目融合规划完成**：已创建新仓库 `RayDutchman/plm-unified`，本地路径 `/home/chenweibo/plm-unified`，M0 全部完成（2026-06-26）。后续开发在新仓库进行，本项目进入维护模式。
- [x] **vault 路径空格转下划线碰撞**：`Tools.unAccent()` 去掉空格→下划线转换（2026-07-04）
- [x] **3D 预览按钮对无 GLB 单零件误显示**：`part_list_item.js` 加 `hasGeometry()` 判断（2026-07-04）
- [x] **转换服务重建后消息不投递**：定位为 Java runner jar 的 SmallRye bug，用混合镜像临时绕过（2026-07-04），根治方案见迁移 plan
- [x] **转换服务迁移为 Python-only**：`2.7.0-py` 镜像上线，aiokafka 手动 commit，回归验证通过（2026-07-04）
- [x] **P0 FastAPI 后端基础设施**：7 个 Task 全部完成，17 个测试通过，`back-py` 容器运行，Nginx auth 路由切换验证通过（2026-07-04）
- [x] **P1a 零件核心 CRUD**：6 个 Task 全部完成，38 个测试通过，14 个零件端点，Nginx parts 路由切换到 FastAPI back-py（2026-07-04）
- [x] **零件模块 Payara→FastAPI 行为对齐（批次 0-2）**：i18n 基础设施 + ApplicationException 体系 + 全局 handler + 用户语言中间件 + 对拍脚本 + P1a 7 方法错误消息对齐 + DTO 字段固化测试。测试从 38 个增加到 57 个全部通过（2026-07-04）
