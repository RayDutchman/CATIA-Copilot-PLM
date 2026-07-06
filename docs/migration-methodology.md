# 后端迁移方法论：从 Payara(Java) 到 FastAPI(Python)

> **目的**：为前端迁移（Backbone.js → React）提供经过验证的正确方法。

---

## 一、核心方法：预生成清单 + 文件映射 + 7 维审计

**错误做法**（我们实际做的——修了 3 轮才收敛）：先写全部代码 → 审计发现 35+11+14=60 个问题 → 反复修复 → 最后靠用户报 bug 补漏。

**正确做法**：写代码前先生成系统化清单，对照清单逐条验证，所有条件满足才算"对齐完成"。

```
1. 建文件映射表    →  每个 Java 文件对应一个 Python 文件
2. 预生成检查清单   →  grep Payara 源码生成 throw matrix + method list
3. 读 Java 源码     →  理解业务逻辑、SQL、异常、响应字段
4. 写 Python 实现   →  对着 Java 写，写的同时就对齐
5. 7 维代码审计     →  AI agent 对照 throw matrix + method list 逐条检查
6. 按优先级修复     →  Critical → Warning，修复后回归测试
7. 验收"对齐完成"   →  全部 7 个硬性条件满足
8. 切路由 + 前端实测 →  全量通过后一次性切
```

---

## 二、预生成检查清单（步骤 2，写代码前必做）

### 2.1 生成 throw matrix

```bash
# 从 Payara 源码抓取所有 throw 语句，去重统计
grep -rn "throw new" docdoku-plm-server-ejb/ --include='*.java' \
  | sed 's/.*throw new \([A-Za-z]*\).*/\1/' | sort | uniq -c | sort -rn
```

产物：`docs/throw-matrix.md` —— 每个 Payara 异常的抛出次数 + Python 对齐状态。

**写代码前就建立这张表，它将是第 7 维审计的依据。**

### 2.2 生成方法覆盖清单

```bash
# Java Bean 的所有 public 方法签名
grep -A1 "public " <Bean>.java | grep "throws"
```

每个方法标注 Python 是否实现，是否对齐。审计时逐方法检查。

---

## 三、文件映射表

核心资产：`docs/file-mapping.md`。每一行是一个检查单位。

---

## 四、7 维代码审计

**6 维 → 7 维**。新增第 7 维 `Exception throw parity`。

### 第 7 维：Exception throw parity

**操作**：对照 `docs/throw-matrix.md`，逐行检查 Python 是否有等价 `raise`。不是"随机发现报什么"，是系统化清单。

Agent 指令：`Read docs/throw-matrix.md. For each row marked "缺 raise", check the Python file-mapping peer and add the appropriate raise statement.`

**评估**：throw matrix 中所有行都是 ✅ 才算通过。

### 其他 6 维（保持不变）

**Coverage / Data integrity / Error handling / API contract / Write verification / Value fidelity** —— 与之前一致，但配合 throw matrix 使用时，agent 不再需要随机发现异常缺陷。

---

## 五、"对齐完成"标准（硬性条件）

全部满足才算完成，缺一条就是没对齐：

| # | 条件 | 验证方法 |
|---|------|---------|
| 1 | 所有 Java public 方法有 Python 等价实现 | file-mapping.md 逐行 ✅ |
| 2 | 所有 Payara throw 有 Python raise | `throw-matrix.md` 全部 ✅ |
| 3 | 所有 i18n key 注册异常类 | `test_i18n_bypass.py` PASSED |
| 4 | 无硬编码中文/英文 HTTPException | `test_i18n_bypass.py` PASSED |
| 5 | 所有 DTO 字段匹配（name/type/nesting） | HTTP 对比 + 值语义审计 |
| 6 | 所有不可实现项入 REMINDERS | `grep TODO app/` 行数 ≤ `grep TODO REMINDERS.md` |
| 7 | 全量测试通过 | `pytest tests/ -q` 144 passed |

---

## 六、TODO 追踪

**任何代码中的 TODO/FIXME/HACK 注释**，必须在 `docs/REMINDERS.md` 中有对应条目。回生规则：每次提交前检查 `grep TODO app/ | wc -l` 与 `grep TODO REMINDERS.md | wc -l` 的一致性。

---

## 七、工具链

| 工具 | 用途 |
|------|------|
| `docs/throw-matrix.md` | **新增**——预生成的异常对照表 |
| `docs/file-mapping.md` | 文件映射表 + 7 维审计 Prompt |
| `tests/test_i18n_bypass.py` | **新增**——零容忍 i18n 绕过 |
| `scripts/full_compare_v2.py` | HTTP 层兜底对比 |
| `pytest tests/ -q` | 回归测试 |
