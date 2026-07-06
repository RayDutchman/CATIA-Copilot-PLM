# 后端迁移方法论：从 Payara(Java) 到 FastAPI(Python)

> **目的**：为前端迁移（Backbone.js → React）提供经过验证的正确方法。

---

## 一、核心方法：文件映射 + 6 维代码审计

用 HTTP 对比或 pytest 作为验收标准是不够的——它们只能验证"端点返回 200"，测不出 SQL 逻辑差异、值语义错误、stub 持久化缺失。

唯一可靠的方法：**读 Java 源码，对着 Java 写 Python，写完立即审计**。

### 全流程

```
1. 建文件映射表   →  每个 Java 文件对应一个 Python 文件
2. 读 Java 源码    →  理解业务逻辑、SQL、异常、响应字段
3. 写 Python 实现  →  对着 Java 写，写的同时就对齐
4. 6 维代码审计    →  AI agent 读 Java + Python 双向对比，输出差异
5. 按优先级修复    →  Critical → Warning，修复后回归测试
6. 全量测试通过    →  144 passed, 0 failed
7. 切路由 + 前端实测 →  全量通过后一次性切
```

关键原则：**Java 源码是唯一验收标准**。不是"端点返回 200"，不是"pytest 通过"，是"Python 代码与 Java 代码逻辑等价"。

---

## 二、文件映射表

核心资产：`docs/file-mapping.md`。每一行是一个检查单位。

```
| # | Java Bean | Java REST Resource | Python Service | Python Router | 功能域 |
|---|-----------|-------------------|----------------|---------------|--------|
| 1 | ProductManagerBean.java | — | product_manager.py | — | 零件 CRUD |
| 3 | — | PartsResource.java | — | parts.py | 零件列表/搜索 |
```

**前端迁移时**：`Backbone Model/View ↔ React Component/Hook`，同样的表格结构。

---

## 三、6 维代码审计

审计 Prompt 要求 AI agent **读 Java 源码 + Python 源码**，双向对比，从 6 个维度发现差异：

**Coverage** — Python 实现了 Java 的全部方法吗？逻辑等价即可，不要求命名一致。

**Data integrity** — 每条 SQL 查询：同一张表？相同的 JOIN/WHERE/ORDER？Java 是真值。

**Error handling** — Java 的每个 throw → Python 的 raise，i18n key 对齐。遗漏的异常和静默吞掉的错误都要标记。

**API contract** — Java DTO 的每个字段在 Python dict 里有同名 camelCase key 吗？嵌套深度一致？类型一致（object/array/scalar）？

**Write verification** — Python 返回了 200/204，但调了 `db.commit()` 吗？硬编码的 `[]`/`{}`/`{"status":"ok"}` 是 Stub，必须标记。

**Value fidelity** — 每个响应字段的值从哪来？查了正确的 DB 表？做了正确的类型转换？枚举映射了吗？日期格式是 ISO 8601 吗？

**审计维度描述必须是开放式的**，不能列举具体检查项——那会把 AI agent 框死在清单内，遗漏清单外的问题。

---

## 四、工具链

| 工具 | 用途 |
|------|------|
| `docs/file-mapping.md` | 文件映射表 + 6 维审计 Prompt |
| `scripts/full_compare_v2.py` | HTTP 层 96 端点兜底对比（辅助，不是主要验证手段） |
| `pytest tests/ -q` | 回归测试（144 passed） |

---

## 五、前端迁移适配

核心方法不变：**建映射 → 读旧代码 → 写新代码 → 6 维审计 → 修复 → 全量通过 → 一次性切**。调整点：

| 后端维度 | 前端维度 |
|---------|---------|
| 方法覆盖率 | 组件覆盖率（每个 Backbone View → React Component） |
| SQL 查询逻辑 | 状态管理逻辑（Backbone Model get/set → Redux/Zustand store） |
| 异常对齐 | 错误处理对齐（错误码、toast、全局 error handler） |
| API 契约 | Props/State 字段完整性 |
| Write 验证 | 空组件检测（渲染了但不发 API 请求） |
| 值语义正确性 | 交互行为一致性（截图对比 + 流程录制） |

**额外工具**：Playwright 录制旧前端每页截图 + 关键交互 → 新前端逐页对比。

**额外验收标准**：前端比"长得像不像"和"交互行为是否一致"。
