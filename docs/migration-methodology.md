# 后端迁移方法论：从 Payara(Java) 到 FastAPI(Python)

> **目的**：存档后端迁移过程中经过验证的有效方法、无效尝试和关键教训，为前端迁移（Backbone.js → React）提供可复用的知识资产。

---

## 一、方法评估矩阵

| 方法 | 投入 | 发现问题数 | 遗漏 | 评价 |
|------|------|-----------|------|------|
| **pytest 单元/集成测试** | 中 | 30+ | **Stub 不报错**——返回 200/204 就通过，不检查持久化 | 必要但不够 |
| **Payara 对拍（HTTP 层）** `compare_all_endpoints.py` | 中 | 50+ | 只比 GET，POST/PUT/DELETE 不测；SQL 逻辑差异看不出来 | 必要但不够 |
| **前端实测（Playwright）** | 高 | 10+ | 依赖人工观察，覆盖不系统 | 辅助验证 |
| **读-写-读 一致性测试** `audit_write_stubs.py` | 中 | 3 | 有 bug（误报），需要完善 | 有潜力但需打磨 |
| **文件映射+代码级对比** | 高 | **200+** | **无遗漏** | ✅ 唯一可靠方法 |

---

## 二、文件映射+代码级对比（唯一可靠方法）

### 核心思路

HTTP 层对拍、测试、前端实测都只能验证「端点能不能跑」。只有**直接读 Java 源码和 Python 源码逐方法对比**，才能发现：

- SQL 查询逻辑差异（COUNT PartRevision vs PartMaster）
- 权限校验缺失（Java 有 ACL 检查，Python 直接 return）
- 持久化缺失（返回 200/204 但不调 db.commit()）
- DTO 字段差异（Java 有 24 个字段，Python 只返回 12 个）
- Stub 实现（return [] / {"status":"ok"} 无任何真实逻辑）

### 实施步骤

1. **建立文件映射表**（`docs/file-mapping.md`）：Java 文件名 → Python 文件名，按功能域归类
2. **定义检查维度**（5 维度）：
   - 方法覆盖率：Java 有→Python 缺
   - SQL 查询逻辑：表名、JOIN、WHERE 条件是否一致
   - 异常对齐：Exception 类型和 i18n key
   - 响应字段：DTO 字段 vs dict key 是否对应
   - Stub 检测：return [] / {"status":"ok"} 无 db.commit()
3. **派 AI agent 逐对检查**：每对文件派一个 agent，读取 Java + Python 源码输出差异报告
4. **按优先级批量修复**：Critical（数据正确性/安全问题）→ Partial（功能不完整）→ OK（无需修复）

### 检查 Prompt 模板

```markdown
Audit the Java→Python migration file pair.

Java file: {路径}
Python file: {路径}

Check 5 dimensions:
1. Method coverage — all Java public methods → Python equiv?
2. SQL logic — same tables/JOINs/WHERE? 🚨 Payara code = ground truth
3. Exception alignment — Java throw → Python raise with same i18n key?
4. Response fields — Java DTO fields → Python dict keys match?
5. Stub detection — Python returns hardcoded []/{}/{"status":"ok"} without db.commit()?

Output: METHOD | STATUS (✅/❌/⚠) | DETAIL
```

### 文件映射表格式

```markdown
| # | Java File | Python File | Domain | Last Audit |
|---|-----------|-------------|--------|-------------|
| 1 | ProductManagerBean.java | product_service.py | Parts CRUD | 2026-07-05 |
```

---

## 三、反模式（我们踩过的坑）

### 1. Stub 伪实现
**症状**：POST/PUT/DELETE 返回 200/204，但数据不持久化。前端弹窗关闭→刷新→数据消失。
**根因**：subagent 驱动的实现以「不报错」为标准，非「功能正确」。
**教训**：每个写操作必须验证 `db.commit()` 存在。读-写-读一致性测试可自动化检测。

### 2. 猜 Payara 逻辑而不读源码
**症状**：stats 计数猜了「有已签入迭代」，实际 Payara 就是 `COUNT(*) FROM partrevision`。
**根因**：快——不想花时间读 Java 代码。
**教训**：凡是和 Payara 对不上的，**必须先 grep Payara 源码**，不允许推测。

### 3. 只测 GET 不测 POST/PUT/DELETE
**症状**：`compare_all_endpoints.py` 只比 133 个 GET 端点，写端点全漏。
**教训**：对拍必须包含写操作。`full_compare_v2.py` 已覆盖。

### 4. 尾斜杠 307 忽略
**症状**：前端 Backbone POST/PUT 带 `/` → FastAPI 307 → Location 丢端口 → 挂起。
**教训**：所有 POST/PUT/DELETE 必须双路由。GET 也应统一加 `/`（Starlette 自动接受）。

### 5. 响应字段偷工减料
**症状**：Python 返回 `{"status":"ok"}` 而不是完整 DTO。前端 Backbone Model 期望的字段缺失→静默失败。
**教训**：实现端点前必须先读前端 Model 的 `parse()/initialize()` 提取必需字段列表。

---

## 四、工具链

| 工具 | 路径 | 用途 |
|------|------|------|
| 文件映射表 | `docs/file-mapping.md` | Java→Python 文件对应关系 |
| HTTP 对拍 | `scripts/full_compare_v2.py` | 96 端点 GET/POST/PUT/DELETE 全覆盖 |
| Stub 审计 | `scripts/audit_write_stubs.py` | 读-写-读 一致性测试 |
| GET 尾斜杠 | `scripts/add_get_trailing_slash.py` | 自动补 GET 尾斜杠双路由 |
| 种子数据 | `scripts/seed_test_data.py` | 对拍用测试数据 |

---

## 五、标准工作流（从前端迁移可复用）

```
1. 建文件映射表 → Java/Payara 源文件 ↔ 新框架源文件
2. 读 Payara 源码 → 理解真实业务逻辑（不允许推测）
3. 实现 MVP → 只做核心 CRUD + 正确状态码
4. 文件映射+代码对比 → AI agent 逐对检查 5 维度
5. 全量对拍 → full_compare + 种子数据
6. 读前端 Model → 确保响应字段完整（Backbone parse/initialize）
7. 尾斜杠补全 → POST/PUT 双路由，GET 全量加 /
8. 前端实测 → Playwright 走核心流程
9. 切 Nginx 路由
10. 更新文档
```

---

## 六、前端迁移适配要点

Backbone.js → React 迁移时，后端经验可直接复用的部分：

### 可直接复用
- 文件映射表模式（Backbone Model ↔ React Component/Service）
- 5 维度检查（调整维度：状态管理对比、事件处理对比、UI 行为对比）
- 全量对拍思路（旧前端截图/行为记录 → 新前端逐页对比）
- 尾斜杠处理（前端路由的路径一致性问题）

### 需调整的部分
- 「SQL 查询逻辑」→「状态管理逻辑」（Redux/Zustand store vs Backbone Model 的 get/set）
- 「异常对齐」→「错误处理对齐」（错误码、toast 消息、全局 error handler）
- 「DTO 字段」→「Props/State 字段」（组件 props 完整性和类型）
- 「Stub 检测」→「空组件/加载状态缺失」

### 关键差异
- 后端是「写的对不对」——通过对比 Java 源码验证
- 前端是「**长得像不像**」和「**交互行为是否一致**」——需要截图对比 + 交互流程录制

### 建议
1. 先建 Backbone Model/View/Collection ↔ React Component/Hook/Store 映射表
2. 用 Playwright 录制旧前端的每个页面的截图 + 关键交互流程
3. 对每个页面，AI agent 对比：截图是否一致、交互行为是否一致、数据流是否一致
4. 重点审计：Backbone `parse()` 中访问的字段→React 组件是否接收对应 props
