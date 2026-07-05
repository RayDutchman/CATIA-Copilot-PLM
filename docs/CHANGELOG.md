# Changelog

按日期倒序记录所有功能变更、Bug 修复和配置改动。

格式：`## YYYY-MM-DD`，条目以 `feat:` / `fix:` / `chore:` / `docs:` 前缀标注。

---

## 2026-07-05 — P3 产品结构 + P4 变更管理 + 阶段收尾

### P3 产品结构（ConfigurationItem/Baseline/Configuration/Instance）

- feat: ORM 5 模型（ConfigurationItem/ProductBaseline/ProductConfiguration/ProductInstanceMaster/ProductInstanceIteration）+ CADInstance 复用
- feat: ProductStructureService — filter_product_structure（24字段 ComponentDTO 递归）、decodePath、CI/Baseline/Config/Instance CRUD
- feat: 4 路由文件（products/instances/files）+ main.py 注册 + Nginx 2 路由块切换
- fix: P3 Payara 对拍 14 项差异——filter 对象 vs 数组、depth 参数生效、configSpec 参数、字段命名（partNumber→designItemNumber）、author 查 Account.name、DELETE 204、不足字段补全
- fix: LightPartMasterDTO 字段 number/name→partNumber/partName（修复前端 typeahead "undefined"）
- fix: create_ci 接受 designItemNumber + 验证 PartMaster 存在性

### P4 变更管理（Issue/Request/Order/Milestone）

- feat: ORM 4 模型（ChangeIssue/Request/Order/Milestone）+ 3 标签关联表
- feat: ChangeService — 通用 CRUD + 标签管理（12 方法）
- feat: changes.py 路由 — ~30 端点（含尾斜杠双路由）+ Nginx 正则块切换
- fix: _item_to_dict/_milestone_to_dict 完全对齐 Payara camelCase（c.name→手动 getattr）

### 跨模块对齐债务清偿

- fix: deletePartRevision 4 项约束已实现——EntityConstraintException1/5/22（配置项根/基线/替代品，P3）+ EntityConstraintException21（变更项，P4）
- fix: 前端 Model 审计——author 对象缺失致 Part/CI/PartTemplate/Configuration/Baseline 崩溃已修复

### 文档收尾

- docs: CHANGELOG.md 补全 P3/P4 全量记录
- docs: REMINDERS.md P3/P4 完成归档、对齐债务清理、P5 列为下一阶段
- docs: 路线图 P3/P4 状态→✅、Nginx 路由表补 P3/P4 块、对齐债务 P3/P4 条目剔除
- test: 90 测试通过（3 个文档旧数据残留，非本次变更）

## 2026-07-05 — P3 对拍报告剩余差异修复

- fix: products.py DELETE 返回 204 No Content（对齐 Payara）
- fix: products.py GET list/detail 字段重命名 partNumber→designItemNumber，补 designItemName/designItemLatestVersion/author/hasModificationNotification/pathToPathLinks
- fix: product_structure_service.py author 改为从 PartMaster.author→Account.name（对齐 Java pm.getAuthor().getName()）
- fix: product_structure_service.py authorLogin 改为 rev.part_master.author_login
- fix: product_structure_service.py checkOutUser 补全 UserDTO（login/workspaceId/name/email/language）
- fix: product_structure_service.py virtual/substitute 从 usage_link 属性获取（当前默认 False）

## 2026-07-05 — P2 文档/文件夹 + 系统化对拍

- feat: P2 文档/文件夹/模板——ORM(5模型+2关联表)、document_service(14方法)、4路由(27端点)、80测试通过
- feat: Nginx 4路由块切换(documents/folders/document-templates/files/documents)
- feat: 系统化 Payara 对拍——零件端点(P0路由5处+P1补端点4处+P2字段差异exclude_none)、文档端点(P0 search camelCase+P0 folder ID+P1补端点5处+P1字段)
- fix: 尾斜杠307——POST /parts/ /documents/ /nativecad/ /attachedfiles/ /documents/upload/ 加双路由
- fix: CAD转换无文件→204 No Content(Payara对齐)
- fix: 零件列表 exclude_none 回滚(删acl/checkOutUser致前端无权限)
- fix: 文件夹返回Payara格式(id/name/path/home)含子文件夹
- fix: 文档创建响应 camelCase 含 documentIterations+id 格式
- fix: 文档缺失端点补全(checkedout/countCheckedOut/doc_revs/aborted-workflows/inverse-links)
- fix: 零件缺失端点补全(used-by/tags/instances/baselines/aborted-workflows)
- fix: CATIA Copilot端点 8001→8000(Payara→FastAPI)
- known: 3D预览不显示——Nginx/uvicorn HTTP代理层与Three.js r90交互问题(bytely一致/headers对齐/Payara→FA切换可复现,需抓包或升级Three.js)

- feat(py): Kafka 转换消息重构为嵌套结构+userToken，topic 改 CONVERT
- feat(py): file_service——vault 写读 + BinaryResource 记录（save_nativecad/save_attached/get_file_bytes）
- feat(py): 文件上传/下载端点 + 触发转换（nativecad 上传带 CAD 白名单校验，attachedfiles 上传下载，GLB 直下）
- feat(py): 转换回调服务+端点——handle_callback 含 race 修复（findPendingConversion）和空几何跳过逻辑，对齐 Payara ConverterBean
- feat(py): release/obsolete/newVersion 端点对齐 Payara i18n（NotAllowedException46/41/38/36）
- feat(py): 标签管理端点（set/add/remove tags，_ensure_tag upsert）
- feat(py): 零件搜索端点（DB LIKE MVP，按 name/number/type 模糊匹配）
- chore(docker): Nginx files 路由指向 back-py，conversion.env ENDPOINT 切换为 back-py:8000
- chore: requirements 新增 python-multipart 依赖
- test: 73 个测试全部通过（新增 test_part_files_api/test_file_service/test_conversion_service/test_part_status/test_part_tags/test_part_search）

## 2026-07-04（续6）— 迁移路线图权威文档

- docs: 新建 `docs/superpowers/fastapi-migration-roadmap.md` 作为迁移路线图唯一事实来源
- docs: 根据 P0/P1a/对齐审计执行教训调整路线图——引入"标准每阶段工作流"（对齐审计+Payara 对拍在切 Nginx 之前）
- docs: 沉淀 i18n/异常基础设施为跨阶段共享地基与强制规范
- docs: 新增"对齐债务追踪"表（跨模块约束打桩+TODO，标注属主阶段 P3/P4/P5）
- docs: 显式化阶段依赖关系（P3/P4/P5 落地时回补 parts 对齐债务）
- docs: REMINDERS 同步——批次 0-2 归档、P1b 待规划、对齐债务条目

## 2026-07-04（续5）— 零件模块 Payara→FastAPI 行为对齐（批次 0-2）

- feat: i18n 基础设施——复制 Java 4 语言 properties 文件，实现 `app/core/i18n.py` 加载器
- feat: 业务异常体系——`ApplicationException` 基类 + 6 子类，镜像 Payara 异常 key 约定
- feat: 全局 exception handler——异常→HTTP 状态码映射（403/404/409/500），按用户语言翻译 i18n
- feat: 用户语言中间件——从 JWT 解析 Account.language 注入 `request.state.user_language`
- test: 与 Payara 对拍脚本 `scripts/compare_with_payara.py`
- feat: deletePartRevision——`EntityConstraintException2` 被用作组件时返回中文错误消息
- feat: checkout/checkin/undo_checkout——全部替换为 i18n 异常（NotAllowedException37/47/20/19/41）
- feat: createPartMaster/updatePartIteration——EntityAlreadyExistsException/NotAllowedException25
- test: 固化 geometryFileURI/UserDTO/datetime 对齐行为
- test: 批次 1 错误路径集成测试（test_parts_error_paths.py，3 个测试场景）
- 测试统计：从 38 个增加到 57 个，全部通过

---

- feat: P1a 零件核心 CRUD 全部完成（6 个 Task，38 个测试全通过）
  - ORM 模型：9 张零件表 + 5 张关联表完整映射（`app/models/part.py`）
  - Pydantic Schemas：PartRevisionDTO/PartCreationDTO/ComponentDTO 等（`app/schemas/part.py`）
  - ProductService：CRUD + 签出签入 + 装配同步（`app/services/product_service.py`）
  - DTO 映射工具：ORM → Pydantic 转换（`app/services/part_mapper.py`）
  - 14 个零件端点：list/count/search/checkedout/create/get/delete/checkout/checkin/undo/update/conversion
  - Nginx 零件路由切换到 FastAPI back-py（正则只匹配 parts 路径）
- fix: ORM 关联表列名修正——`partrevision_tag` 用 `partmaster_workspace_id`/`partmaster_partnumber`（非 `partrevision_` 前缀）
- fix: ORM 关联表列名修正——`partusagelink_cadinstance` 用 `cadinstance_id`（单数，非 `cadinstances_id`）
- fix: SQLAlchemy 字符串表达式无法引用 Table 对象，改用 lambda 传递 primaryjoin/secondaryjoin
- fix: PartRevision.iterations 添加 `cascade=all,delete-orphan`（删除 revision 时级联删除 iterations）
- fix: 测试用 `test1` 登录（Workspace_2 成员），admin 不是该 workspace 成员
- fix: 测试密码用 `password`（非 `changeit`），workspace 用 `Workspace_2`（DB 中实际存在）

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
