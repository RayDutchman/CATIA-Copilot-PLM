# 设计：Payara → FastAPI 零件模块行为对齐审计

日期：2026-07-04
状态：设计已确认，待写实现计划

## 背景与问题

CATIA-Copilot-PLM 正在把 Payara(Java EE) 后端逐步迁移到 FastAPI（`docdoku-plm-server-py/`）。前端 Backbone.js 零改动，通过 Nginx 按路径前缀把 parts 请求切到 FastAPI。

P1a 完成了零件核心 CRUD，但 Nginx 路由切换（Task 6）先于行为对齐审计，导致前端一访问就暴露 gap：

- **geometryFileURI 始终为 null**：前端拿不到 GLB 路径，3D 预览失效（用户误以为"转换服务失效"，实则转换正常，是响应字段缺失）。已临时修复。
- **删除被引用零件返回 500**：Payara 返回本地化业务错误"您无法删除在装配体中用作组件的零件"，FastAPI 直接 FK 违例崩 500。曾用硬编码中文临时修，已回滚（硬编码违背多语言，且未复用现成 i18n）。
- **UserDTO 缺 name/email/language**、**datetime 无 UTC Z 后缀**、**notifications 为空** 等多处响应差异。

根本问题：FastAPI 侧是"bug 触发式修补"，缺乏对 Payara 业务逻辑、错误处理、i18n、响应 DTO 的系统性对齐。

## 目标

系统性审计并对齐零件模块的 15 个核心方法，覆盖：业务校验逻辑、异常/错误消息（i18n）、响应 DTO 字段。让 FastAPI 的行为与重构前 Payara 一致，前端零改动即可正常使用。

## 范围

**In scope**：零件相关 15 个核心方法（P1a 已实现 7 + P1b 待实现 8）：

| 类别 | 方法 |
|---|---|
| P1a 已实现（7） | createPartMaster、deletePartRevision、checkOutPart、checkInPart、undoCheckOutPart、updatePartIteration、getConversion（转换状态查询） |
| P1b 待实现（8） | saveNativeCADInPartIteration（上传CAD）、saveFileInPartIteration（上传附件）、handleConversionResultCallback（转换回调）、createPartRevision（新版本）、releasePartRevision（发布）、markPartRevisionAsObsolete（废弃）、removeFileInPartIteration（删文件）、标签管理 |

**Out of scope**：Account/Workspace/Document 等非零件模块；产品/配置项/基线；变更管理。

## 架构决策：i18n + 异常体系（方案 A）

镜像 Payara 的 `ApplicationException` + `PropertiesLoader` 设计，让 Python 的 `raise XxxException("key")` 与 Java 的 `throw new XxxException("key")` 一一对应，使"逐方法对照"审计可落地。

### 组件

**`app/core/i18n.py`** — i18n 加载器
- 复制 Java 的 `LocalStrings_{en,fr,zh,ru}.properties`（来自 `docdoku-plm-server-core/.../core/i18n/`）到 Python 项目资源目录。
- `get(key: str, lang: str, *args) -> str`：按 lang 选文件，查 key，用 `str.format` 填充 `{0}{1}` 占位符。
- 语言选择规则对齐 Payara `PropertiesLoader`：`fr`/`ru`/`zh` 各自映射，其余（含 None）兜底 `en`。
- 支持语言列表：`["fr", "en", "ru", "zh"]`（与 Payara `SUPPORTED_LANGUAGES` 一致）。

**`app/core/exceptions.py`** — 异常体系
- 基类 `ApplicationException(key: str, *args)`：只存 i18n key + 格式化参数，不存翻译文本。
- 子类：`EntityConstraintException`、`NotAllowedException`、`AccessRightException`、`*NotFoundException`、`*AlreadyExistsException`、`CreationException` 等。
- 异常 key 约定对齐 Java：默认 key = 类名（如 `PartRevisionNotFoundException`）；`EntityConstraintException`/`NotAllowedException` 用带编号 key（如 `EntityConstraintException2`、`NotAllowedException20`）。

**`app/main.py`** — exception handler
- 注册 `ApplicationException` 的全局 handler。
- 根据异常类查 HTTP 状态码映射表 → 用当前用户 `Account.language` 翻译 key → 返回响应体。
- 响应体字段格式（`message` vs `error`）在批次 0 审计时对拍 Payara 确认。

### 异常 → HTTP 状态码映射

| 异常类 | HTTP 状态 |
|---|---|
| `AccessRightException` | 403 |
| `NotAllowedException` | 403 |
| `EntityConstraintException` | 403 |
| `*NotFoundException` | 404 |
| `*AlreadyExistsException` | 409 |
| `CreationException` | 500 |
| 其他未捕获 | 500 |

### 被否决的方案

- **方案 B（HTTPException + i18n 函数）**：service 层耦合 HTTP 状态码、需把 lang 透传进 service，与 Java 结构不同构，审计对照困难。
- **方案 C（返回 i18n key 前端翻译）**：违背"前端零改动"约束（Payara 原本返回已翻译文本），直接否决。

## 审计方法论

每个方法一个"对齐单元"，核对 4 层：业务校验、异常/i18n key、DTO 字段、HTTP 状态。产出一张对齐矩阵表存进后续实现产物。

### 对齐矩阵表结构

| 列 | 内容 |
|---|---|
| 方法 | 如 `checkOutPart` |
| Java 校验点 | 非最新版→NotAllowedException72；已签出→37；已发布/废弃→47 |
| Python 现状 | 已实现哪些校验、缺哪些 |
| i18n key gap | Python 缺失/用错的 key |
| DTO 字段 gap | 响应字段缺失/格式不符 |
| 状态 | ✅对齐 / ⚠️部分 / ❌缺失 |

### 分批执行（每批一个可独立验证的单元）

1. **批次 0 — 基础设施**：i18n 加载器 + ApplicationException 体系 + exception handler + 复制 4 个 properties 文件。所有后续批次的前提。
2. **批次 1 — P1a 已实现 7 方法对齐**：把现有 `HTTPException` 硬编码全换成 i18n 异常，补齐缺失校验。
3. **批次 2 — DTO 字段对齐**：UserDTO/notifications/datetime 格式等响应层 gap（geometryFileURI/UserDTO/datetime 已在前一轮临时修，需纳入审计确认与固化）。
4. **批次 3 — P1b 8 方法**：文件上传/转换回调/发布/废弃/标签，新写端点时直接按对齐规范写。

### 子 agent 分工

每批"审计"环节派 explore 子 agent 精读对应 Java 方法产出校验清单，主 agent 负责写 Python 代码。

## 关键校验点与 i18n key 清单（审计基线）

来自 Java 源码梳理，作为对齐基准：

### deletePartRevision（ProductManagerBean L2105）
- 配置项根零件 → `EntityConstraintException1`
- 被用作组件 → `EntityConstraintException2`
- 被用作替代品 → `EntityConstraintException22`
- 已在基线中 → `EntityConstraintException5`
- 已分配到变更项 → `EntityConstraintException21`

### checkOutPart（L475）
- 非最新修订版 → `NotAllowedException72`
- 已签出 → `NotAllowedException37`
- 已发布或已废弃 → `NotAllowedException47`

### checkInPart（L576）
- 非当前用户签出 → `NotAllowedException20`
- 循环装配 → `EntityConstraintException12`

### undoCheckOutPart（L387）
- 迭代数 ≤ 1 → `NotAllowedException41`
- 非当前用户签出 → `NotAllowedException19`

### updatePartIteration（L895）
- 非签出用户（带零件号参数）→ `NotAllowedException25`
- 属性无效 → `NotAllowedException59`

### createPartMaster（L273）
- 工作流任务无工作者 → `NotAllowedException56`
- 模板掩码不匹配 → `NotAllowedException42`
- 零件已存在 → `PartMasterAlreadyExistsException`

### createPartRevision（L2176）
- 原版本已签出 → `NotAllowedException40`
- 原版本无迭代 → `NotAllowedException41`

### releasePartRevision（L1496）
- 已签出 → `NotAllowedException46`
- 无迭代 → `NotAllowedException41`
- 已废弃 → `NotAllowedException38`

### markPartRevisionAsObsolete（L1519）
- 未发布 → `NotAllowedException36`

### 文件上传（saveNativeCADInPartIteration L645 / saveFileInPartIteration L769）
- 非签出用户或非最新迭代 → `NotAllowedException4`
- CAD 白名单：`stp, step, igs, iges, stl, off, ply, obj, dae, ifc`，否则 400

### 转换回调（handleConversionResultCallback，ConverterBean L152）
- 用 `findPendingConversionForRevision` 定位 pending iteration（避免 race condition，已知修复）
- 空几何体 `no geometry generated` → `endConversion(key, true)` 标记成功跳过
- **不检查签出状态**（走 `loadConvertiblePartIteration`，只验 ACL 写权限 + 转换记录存在）
- 循环装配 → `EntityConstraintException12`

## i18n 关键事实

- properties 文件路径：`docdoku-plm-server-core/src/main/resources/com/docdoku/plm/server/core/i18n/LocalStrings_{en,fr,zh,ru}.properties`（各 180 行）。
- 无 `LocalStrings.properties` 裸基文件；`PropertiesLoader` default case = `_en`。
- `Account.language` 存纯语言代码字符串（`"en"`/`"fr"`/`"zh"`），无地区后缀。DB 现有：zh×9、fr×4、en×1。
- Java 用自定义 `PropertiesLoader.loadLocalizedProperties`（非标准 ResourceBundle），switch case 硬编码后缀。
- Java properties UTF-8 无 BOM，Python 可直接解析（注意 `{0}{1}` MessageFormat 占位符）。
- 异常本地化调用链：REST 请求 → LocaleProvider（优先 Account.getLocale()，回退 Accept-Language）→ ExceptionMapper → ApplicationException.getMessage(Locale) → PropertiesLoader。

## 验证策略

### 1. 单元/集成测试（每批必做）
- i18n 基础设施：`get(key, lang)` 4 语言翻译正确、`{0}` 参数填充、缺失 key 兜底。
- 每方法错误路径：构造触发条件（删被引用件、签出已签出件等），断言正确 HTTP 状态码 + 正确 i18n key 翻译文本。
- 真实 DB（Workspace_2 / test1），沿用现有 pytest 模式。

### 2. 与 Payara 对拍
- 同一操作分别请求 FastAPI（:8000 经 Nginx）和 Payara（:8001 直连），对比响应体 + 状态码。
- 已验证有效（发现 geometryFileURI/UserDTO/datetime 三个 gap）。
- 对拍脚本作为每批验收工具。

### 3. 前端实测（用户负责）
- 每批交付后，主 agent 列出"该测哪些前端操作 + 预期行为"，用户照着点。最终验收关。

### 整体验收标准
- 15 个方法对齐矩阵全部 ✅
- 每方法错误路径有测试覆盖
- 对拍脚本对关键操作无 diff（除已知可接受差异如 datetime 精度）
- 4 种语言错误消息都能正确返回

## 已知约束与事实

- 测试：`workdir: docdoku-plm-server-py` → `source venv/bin/activate && pytest tests/ -q`（venv 在子目录，根目录跑会失败）。
- admin 密码 `password`；test1（密码 password）是 Workspace_2 成员，写零件测试用 test1。
- 重建 back-py：`workdir: docdoku-plm-docker` → `docker compose up -d --build back-py`。
- Nginx parts 路由已切到 FastAPI（保留不回滚，便于用户前端实测发现 gap）。
- 前一轮临时修复（未提交）：geometryFileURI、UserDTO name/email/language、datetime UTC、modificationDate 取末迭代——需在批次 2 审计确认后固化。
