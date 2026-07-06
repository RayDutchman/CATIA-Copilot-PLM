# 后端迁移方法论：从 Payara(Java) 到 FastAPI(Python)

> **目的**：存档后端迁移过程中经过验证的有效方法、无效尝试和关键教训，为前端迁移（Backbone.js → React）提供可复用的知识资产。
> **最后更新**：2026-07-06（路线图反思 + 6维审计方法论最终版）

---

## 一、原始路线图的根本错误

`docs/superpowers/fastapi-migration-roadmap.md` 定义了"标准每阶段工作流"：

```
1. ORM 建模 → 2. 端点实现 → 3. 行为对齐审计 → 4. Payara 对拍 → 5. 前端实测 → 6. 切 Nginx
```

**这是错误的**。问题出在步骤顺序：

| 错误 | 后果 | 实例 |
|------|------|------|
| **先实现，后审计** | Subagent 以"不报错"为标准实现，产出大量 stub（返回 200/204 但不调 `db.commit()`） | P1b 的 `PUT /front-options` 返回 204 但不写 DB，用户保存的自定义列消失 |
| **分阶段迁移** | 跨模块依赖导致早期实现不完整。deletePartRevision 需要 P3 的 ConfigurationItem 检查、P4 的 ChangeItem 检查——P1 阶段只能打 TODO，后续阶段经常忘记回补 | P1a 的 deletePartRevision 在 3 轮审计后才补齐 4 个 EntityConstraint |
| **HTTP 对拍为先** | `compare_all_endpoints.py` 只比 HTTP 响应（状态码 + JSON keys），测不出 SQL 逻辑差异、值语义错误、stub 持久化缺失 | `count_parts` 数的是 PartMaster 不是 PartRevision——HTTP 层两个端点都返回 200 + `{"count": N}`，完全看不出来 |
| **Stub 当完成** | 实施 subagent 对自己的"完成"标准是 pytest 通过，不是业务逻辑完整 | 50+ 端点返回 `[]`/`{}`/`{"status":"ok"}` 被标记为 ✅ |

**根本原因**：把"验证"放在"实现"之后。正确顺序应该是**先读 Java 源码，理解业务逻辑，再写 Python 实现**。

---

## 二、正确方法：文件映射 + 6 维审计（实施前读源码）

### 正确的全流程

```
1. 建文件映射表   →  docs/file-mapping.md（Java ↔ Python 文件对）
2. 读 Java 源码    →  理解每对文件的业务逻辑、SQL、异常、响应字段（先读，不写）
3. 6 维审计开工    →  AI agent 逐对检查，输出差异报告
4. 按优先级修复    →  Critical → Partial → Minor，修复后回归测试
5. 全量测试通过    →  142 passed, 0 failed
6. 切 Nginx 路由   →  仅在全量通过后执行
7. 前端实测        →  Playwright 走核心流程
```

关键区别：**步骤 2 和 3 在代码实现之前**。不是"先写一堆端点，再回来修 bug"，而是"读完 Java 源码，对着 Java 写 Python，写的同时就对齐"。

### 6 维度审计（开放式引导，不是清单框定）

```markdown
1. 方法覆盖率 — 读 Java 源码理解全部 public API，逐方法查 Python 等价实现
2. SQL 查询逻辑 — 逐条对比 Java/Python 的 SQL：表名、JOIN、WHERE、聚合、排序。Java = 真值
3. 异常处理 — Java 的 throw/catch → Python 的 raise，i18n key 对齐
4. 响应字段存在性 — 字段名（camelCase）、嵌套深度、类型（object/array/scalar）
5. Stub 检测 — []、{}、{"status":"ok"}、Response(204) 无 DB 操作 = Stub
6. 值语义正确性 — 每个字段的值从哪来？查了正确的 DB 表？做了正确的类型转换？枚举映射了吗？日期格式是 ISO 吗？
```

**⚠️ 关键**：维度描述是开放式引导（"查了正确的 DB 表？"），不是封闭式清单（"查 Account 表了没？"）。封闭式清单会导致 AI agent 只检查清单上的项，遗漏其他值语义问题。

### 为什么 HTTP 对拍不够

| HTTP 对拍能发现 | HTTP 对拍不能发现 |
|----------------|------------------|
| 缺字段（key 不存在） | 字段值语义错误（`acl: 238` vs `acl: {userEntries: [...]}`） |
| HTTP 状态码不一致 | SQL 查询逻辑不一致（COUNT 不同表） |
| Content-Type 差异 | 持久化缺失（返回 204 但不调 `db.commit()`） |
| | 权限校验缺失（返回 200 但跳过了所有 ACL 检查） |

HTTP 对拍是**必要条件**但不是**充分条件**。6 维审计的维度 5（Stub 检测）和 6（值语义正确性）覆盖了 HTTP 对拍的盲区。

---

## 三、分期迁移 vs 全量对齐

### 分期迁移（原始路线图的做法）

```
P0 → P1a → P1b → P2 → P3 → P4 → P5
各阶段独立实现、独立测试、独立切 Nginx
```

**导致的问题**：

1. **Stub 扩散**：每个阶段的实施 subagent 都以"本阶段端点能返回 200"为目标，不关心业务逻辑完整性
2. **对齐债务累积**：P1 依赖 P3/P4 的跨模块检查 → 打 TODO → P3/P4 完成后忘记回补 → 3 轮审计才追回
3. **重复返工**：每个阶段切 Nginx 后发现前端坏（P1a 的 `geometryFileURI` null、P2 的尾斜杠 307）→ 停下来修复 → 再继续下一阶段

### 全量对齐（我们最终成功的方法）

```
建映射 → 读 Java → 全量审计（60 对） → 全量修复 → 全部通过 → 一次切 Nginx
```

**为什么更好**：

1. **无对齐债务**：所有跨模块依赖一次性解决，不存在"等后续阶段补齐"
2. **AI agent 全量扫描**：4 个并行 agent 读 60 对文件，1 轮找 35 个问题，3 轮清 0
3. **实施前就知道正确答案**：读完 Java 源码再写 Python，写的时候就知道 ACL 要构造完整对象、author.name 要查 Account 表

### 前端迁移建议

**不要**像我们后端迁移一样分阶段。**直接做到全量对齐**：

```
建 Backbone→React 映射 → 读 Backbone Model/View 源码 → 全量对齐 → 一次切
```

---

## 四、反模式（我们踩过的所有坑）

### 1. Stub 伪实现
**症状**：POST/PUT/DELETE 返回 200/204，但数据不持久化。前端弹窗关闭→刷新→数据消失。
**根因**：Subagent 以"不报错"为完成标准，非"功能正确"。
**防止**：6 维审计第 5 维（Stub 检测）— 每个写操作必须验证 `db.commit()` 存在。
**前端等效**：React 组件渲染了但不发 API 请求——点击保存后无网络请求。

### 2. HTTP 对拍当验收标准
**症状**：`compare_all_endpoints.py` 显示 60/133 MATCH，但前端仍有 10+ bug。
**根因**：HTTP 层对拍只看状态码和 JSON keys，看不透值语义。
**防止**：6 维审计覆盖 HTTP 对拍盲区（维 5 Stub + 维 6 值语义）。
**前端等效**：截图对比只看"有没有这个元素"，不看"元素内容对不对"。

### 3. 先实现后审计
**症状**：P1-P5 每个阶段都是"先写一堆端点，切 Nginx，发现前端坏，回来修"。
**根因**：路线图把"端点实现"放在"行为对齐审计"之前。
**防止**：反转顺序——先读 Java 源码，写的时候对齐，写完后审计确认。
**前端等效**：先读完 Backbone Model 的 `parse()`/`initialize()`，弄清楚每个 props 从哪来，再写 React 组件。

### 4. 猜 Payara 逻辑而不读源码
**症状**：stats 统计猜测"有已签入迭代才计数"，实际 Payara 就 `COUNT(*) FROM partrevision`。
**根因**：快——不想花时间读 Java 代码。
**防止**：凡是和 Payara 对不上的，**必须先 grep Payara 源码**，不允许推测。

### 5. 审计维度封闭式列举
**症状**：第 6 维写了 `- 用户字段查了Account表？- ACL字段？- Boolean标记？- 枚举映射？` 四个子检查，AI agent 只查这 4 项，遗漏了日期格式、nested entity、file path 等值语义问题。
**防止**：维度描述用开放式语言（"每个字段的值从哪来？"），不用封闭式清单。

### 6. 尾斜杠 307
**症状**：前端 Backbone POST/PUT 带 `/` → FastAPI 307 → Location 丢端口 → 挂起。
**防止**：所有 POST/PUT/DELETE 必须双路由。GET 也应加 `/`。

---

## 五、工具链

| 工具 | 路径 | 用途 |
|------|------|------|
| 文件映射表 | `docs/file-mapping.md` | Java→Python 52 业务对 + 22 基础设施对 |
| 6 维审计 Prompt | `docs/file-mapping.md` 第 四 节 | 开放式引导，AI agent 逐对检查 |
| HTTP 对拍 v2 | `scripts/full_compare_v2.py` | 96 端点 POST/PUT/DELETE/GET 全覆盖 |
| Stub 审计 | `scripts/audit_write_stubs.py` | 读-写-读 一致性测试 |
| GET 尾斜杠 | `scripts/add_get_trailing_slash.py` | 自动补 GET 尾斜杠 |

---

## 六、前端迁移适配

### 可直接复用
- 文件映射表模式（Backbone Model/View ↔ React Component/Hook）
- 6 维审计（调整维度：状态管理对比、事件处理对比、UI 行为对比）
- 开放式 Prompt（不列举具体检查项，引导 AI 自主发现）

### 需调整的部分
- 「SQL 查询逻辑」→「状态管理逻辑」（Redux/Zustand store vs Backbone Model 的 get/set）
- 「异常对齐」→「错误处理对齐」（错误码、toast 消息、全局 error handler）
- 「DTO 字段」→「Props/State 字段」（组件 props 完整性和类型）
- 「Stub 检测」→「空组件/加载状态缺失」

### 关键差异
- 后端：比「写的对不对」— 对比 Java 源码验证
- 前端：比「**长得像不像**」和「**交互行为是否一致**」— 需要截图对比 + 交互流程录制

### 前端迁移建议
1. **不要分期迁移**。建映射后一次全量对齐。
2. **先读 Backbone 源码**，理解每个 Model 的 `parse()`/`initialize()`/`this.get()` 调了什么字段
3. **用 Playwright 录制旧前端**每个页面的截图 + 关键交互流程
4. **6 维审计适配**：方法覆盖率→组件覆盖率、SQL→状态逻辑、值语义→Props 数据流
5. **审计维度用开放式描述**，不列举具体检查项
