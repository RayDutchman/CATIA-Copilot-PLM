# Changelog

按日期倒序记录所有功能变更、Bug 修复和配置改动。

格式：`## YYYY-MM-DD`，条目以 `feat:` / `fix:` / `chore:` / `docs:` 前缀标注。

---

## 2026-07-04（续3）

- feat: P0 FastAPI 后端基础设施全部完成（7 个 Task，17 个测试全通过）
  - `docdoku-plm-server-py/`：FastAPI 骨架 + SQLAlchemy ORM + JWT 安全模块 + 认证端点 + vault 文件服务 + Kafka 生产者
  - JWT 兼容 Payara（HS256 + MD5 密码 + 嵌套 JSON subject），共享 JWT_KEY=changeit
  - `back-py` 容器（端口 8009），Nginx 将 `/docdoku-plm-server-rest/api/auth/` 路由到 FastAPI
  - 端到端验证：Nginx → back-py 登录成功，JWT 响应头正常
- fix: Account ORM 模型修正——`account` 表无 `admin` 列，角色组改从 `usergroupmapping` 表查询
- fix: admin 账号密码为 `password`（非 `changeit`）
- chore: 添加 `pytest.ini`（pythonpath=.）、`kafka-python==2.0.2` 依赖

---

## 2026-07-04（续2）

- feat: `conversion-service-py/` 完全自包含，不再依赖 `docdoku-plm-conversion-service/` 路径
  - `convert_step_glb.py`、`wheels/`、`install-python-deps.sh` 已复制进来
  - `build.sh` 重写为 `docker build .`，无跨目录复制
- feat: 转换服务新增网格格式支持（STL/OFF/PLY/OBJ/DAE/IFC），基于 trimesh+ifcopenshell
  - 新文件 `convert_mesh.py`，统一 `converter.py` 入口按扩展名路由
- fix: 去除 DXF 格式（2D 格式，无法生成 3D GLB）
  - 前端 `part_modal_view.js`、后端 `PartBinaryResource.java`、转换服务同步移除
- fix: 空几何体成功路径未清理 temp_dir（main.py）
- fix: 包围盒计算对 NaN/Inf 顶点的保护（convert_mesh.py）
- chore: 重建前后端 + 转换服务镜像，重启所有服务

---

## 2026-07-04（续）

- feat: 转换服务 Java/Quarkus 编排层迁移为 Python-only（`conversion-service-py/`）
  - 新镜像 `docdoku/docdoku-plm-conversion-service:2.7.0-py`（python:3.11-slim，aiokafka + httpx，无 JVM）
  - `convert_step_glb.py` 新增 `convert()` 函数（Phase 1，保留 CLI 入口兼容）
  - `main.py`：aiokafka 手动 commit，`max_poll_records=1`，显式 offset 提交，根治"消费但不投递"问题
  - `converter.py`：`unaccent()` 对齐修复后的 Java `Tools.unAccent()`（不转下划线）
  - `docker-compose.yml` 切换至新镜像，回滚注释保留
  - 删除其他格式转换器（STL/DAE/IFC/OBJ，CATIA 场景仅用 STEP）
  - 回归验证：`Bevel Gear Formula Student 2008 - 2009` GLB 转换成功，HTTP 200，DB `succeed=true`

---

## 2026-07-04

- fix: `Tools.unAccent()`（`docdoku-plm-server-core`）去掉 `.replaceAll("\\p{javaSpaceChar}", "_")`，vault 路径不再将空格转下划线，消除零件号 "A B" 与 "A_B" 的存储路径碰撞
- fix: 前端 `part_list_item.js` 单零件无 GLB 时隐藏 3D 预览按钮（装配体不受影响，可通过子件组装场景）
- fix: 转换服务改用"混合镜像"——旧 `plm-unified-conversion` 的 runner jar（Kafka 消息投递可靠）+ 重建的 lib jar（含 `unAccent` 修复），解决重建后 SmallRye Reactive Messaging 间歇性"消费但不投递"故障
- chore: 备份回滚资产 `docdoku-plm-conversion-service:2.6.2-jvm-hybrid-rollback` 镜像 tag 及 `rollback-artifacts/app.jar.hybrid-rollback`
- docs: 新增 `docs/architecture/conversion-service-python-migration-plan.md`（转换服务 Java→Python 迁移完整方案，待评审）

---

## 2026-06-26

- docs: 完成构型管理五大职能覆盖分析（EIA-649 / GJB 3206B 对标）
- docs: 完成与 myPDM 项目的多维度对比分析报告
- docs: 完成 `thoughts/新一代 PLM 系统融合路径规划.md`（六阶段融合 roadmap）
- docs: 完成 `thoughts/collaboration-and-milestones.md`（协作约定 + M0–M11 里程碑计划）
- chore: 创建新项目仓库 https://github.com/RayDutchman/plm-unified，完成 M0 全部初始化任务
- chore: 新仓库本地路径：`/home/chenweibo/plm-unified`，后续开发在新仓库进行

---

## 2026-06-25

- fix: 删除 Windows portproxy 规则（8000/8001），解决 front/back 容器因端口被 iphlpsvc 占用而卡在 `Created` 状态无法启动的问题
- docs: REMINDERS.md 补充 portproxy 冲突根因和修复方法，并说明 WSL mirrored 模式下不需要这两条规则

---

## 2026-06-22

### feat: 项目级 AI 记忆机制
- 新建 `.opencode/instructions.md`：项目速查手册，每次打开项目自动注入 agent context
- 新建 `.opencode/opencode.json`：注册 instructions 路径，用 `references` 把 `docs/` 子目录注册给 agent
- 将全局 `~/.config/opencode/instructions.md` 中的 CATIA 路径规范迁移到项目级

### feat: 容器架构文档
- 新建 `docs/architecture/containers.md`：详细说明所有 11 个容器的职责、端口、配置、构建方式、数据卷、关键数据流

### fix: `ConverterBean` 空几何体处理
- **文件**：`docdoku-plm-server-ejb/.../ConverterBean.java`
- **问题**：STEP 文件不含实体（如运动学约束件 MGM_*）时，转换器报 `no geometry generated`，后端写 `succeed=false`，前端显示错误图标
- **修复**：在 `handleConversionResultCallback` 的 errorOutput 判断中检测 `no geometry generated`，改为调用 `endConversion(key, true)` 标记成功跳过

### fix: 装配结构 `amount=0` 导致前端结构树无法展开
- **文件**：`D:\CATIA_Related\CATIA-Copilot\catia_copilot\plm\sync.py`，`_sync_node()` 约第 1110 行
- **问题**：构建子零件条目 `comp_entry` 时缺少 `"amount"` 字段，Java int 默认值 0，前端结构树无 `+` 号
- **修复**：加入 `"amount": len(child.instances) if child.instances else 1`

### docs: 修正 HANDOFF.md 过时内容
- 转换格式 `.obj` → `.glb`
- 转换工具 `FreeCAD` → 内置转换工具（Vert.x 服务）
- 更新转换流程描述，补充 Decimation 已知问题说明
- 删除"零件必须 Checkout 状态"的错误限制说明

---

## 2026-06-18

### fix: `ConverterBean.handleConversionResultCallback` race condition
- **文件**：`docdoku-plm-server-ejb/.../ConverterBean.java`
- **问题**：回调时用 `partRevision.getLastIteration()` 写结果，快速连续上传多个 iteration 时，结果写到最新 iteration，旧 iteration 永远 `pending=true`
- **修复**：在 `ConversionDAO` 新增 `findPendingConversionForRevision(PartRevision)` 方法（JPQL 查 `pending=true` 记录），`ConverterBean` 改用此方法精确定位发起转换的 iteration，同时注入 `ConversionDAO`
- **影响**：修复了 Workspace_2 历史积累的 20 条 `pending=true` 记录问题

### chore: 清理历史 pending conversion 记录
- 直接 DB 操作清掉 20 条 `pending=true, succeed=false` 的 conversion 记录（`UPDATE conversion SET pending=false, succeed=false, enddate=NOW() WHERE pending=true`）

### chore: 后端 JVM 堆内存从 2g 升至 4g
- **文件**：`docdoku-plm-docker/env/back.env`，`HEAP_SIZE=2g` → `HEAP_SIZE=4g`
- **文件**：`docdoku-plm-server/docker/asadmin.commands`，修复旧 `-Xmx2g/-Xms2g` 残留，改为环境变量驱动 `create-jvm-options -- -Xmx${ENV=HEAP_SIZE}`

---

## 2026-06-17（及之前）

### fix: 多处 NPE 修复
- JWT token 解析 NPE
- BasicHeader SAM 模块 NPE
- ProductManagerBean 多处 NPE

### feat: 中文界面支持
- 前后端均支持中文 NLS
- Nginx 配置加入 `charset=utf-8`

### feat: CAD 文件上传格式白名单
- 前端 + 后端双重校验，限制上传文件类型

### fix: 文件名含特殊字符/中文时的 URI 编码问题
- 上传和下载路径均处理 URL 编码

### feat: 前端账号表单校验

### feat: `updateUsageLinksInConvertedIteration`
- 新增 ProductManagerBean 方法，允许在零件已 checkin（非 checkout）状态下更新装配关系
- 用于 conversion 回调时同步装配体子零件位置，绕过 checkout 状态限制
