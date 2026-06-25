# Changelog

按日期倒序记录所有功能变更、Bug 修复和配置改动。

格式：`## YYYY-MM-DD`，条目以 `feat:` / `fix:` / `chore:` / `docs:` 前缀标注。

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
