# AI 批量迁移执行规则

> **目标读者**：执行迁移任务的 AI agent。本文件定义 AI 在无人干预下的自驱动行为规则。

---

## 启动方式

当用户说以下任一指令时，AI 应按本规则开始执行：

- "执行迁移"
- "从 P0A 开始"
- "继续迁移"
- "执行下一批"

---

## 执行循环（AI 自驱动）

```
1. 读取 docs/migration-tracker.csv
2. 筛选 状态 in (待拆分, 待新建)，按 优先级 升序排序
3. 取优先级最低（最靠前）的一批，同域 ≤20 行
4. 如果没剩任务 → 报告"全部完成"，停止
5. 如果是新优先级（如 P0A→P0B 切换）→ 报告用户确认
6. 执行本批（见下文）
7. 跳回步骤 1
```

---

## 单批执行细则

### 输入

从 tracker CSV 取一批行（≤20），每行有：编号、Java源文件、Python目标文件、状态（待拆/待建）、来源文件（仅待拆有）、说明。

### 步骤

#### 并行策略概要

每批内部两个阶段：

| 阶段 | 工具 | 并行度 | 说明 |
|------|------|--------|------|
| **读取** | `explore` subagent | 2-4 并行 | 免费模型，不消耗主 token |
| **写入+验证** | 主 agent 或 1 个 `general` subagent | 串行 | 文件冲突风险，不可并行 |

#### A. 并行读 Java 源码

**路径锚定**（CSV 前缀 → 实际路径）：

| CSV 前缀 | 映射到 |
|---------|--------|
| `core/xxx/` | `docdoku-plm-server-core/src/main/java/com/docdoku/plm/server/core/xxx/` |
| `ejb/xxx/` | `docdoku-plm-server-ejb/src/main/java/com/docdoku/plm/server/xxx/` |
| `rest/xxx/` | `docdoku-plm-server-rest/src/main/java/com/docdoku/plm/server/xxx/` |
| `config/xxx/` | `docdoku-plm-server-config/src/main/java/com/docdoku/plm/server/xxx/` |
| `ext/xxx/` | `docdoku-plm-server-ext/src/main/java/com/docdoku/plm/server/xxx/` |

**并行读取**：将本批 Java 文件分成 3-4 组（每组 ≤5 文件），并行派发 `explore` subagent：

```
Prompt: 读取以下 Java 源文件，返回每个文件的：
  - 类名、父类、JPA 注解（@Entity, @Table, @Column, @ManyToOne 等）
  - 所有字段名和类型
  - 所有 @ManyToOne/@OneToMany 关系（target class）
  - 所有非 getter/setter 的方法签名
  
  文件列表：
  [第1组5个文件路径]
```

所有 subagent 返回结果后，主 agent 汇总 entity 结构 → 开始写代码。

#### B. 读 Python 源码（仅待拆分）

如果状态 = 待拆分，来源文件列指明了当前大文件（如 `models/part.py`）。读取该文件，定位要拆出的 class。

同时 `grep` 所有引用旧 import 路径的位置：`grep -r "from models.part import" app/`。

#### C. 写 Python 目标文件

**待拆分**：从大文件提取对应的 class → 新文件。修改逻辑一字不改，只改 import 路径：
- 新文件内：`from models.part import PartMaster` → `from models.product.part_master import PartMaster`
- 引用方：更新所有 import

**待新建**：读 Java 源码 → 按同域已有 Python 文件的代码风格（SQLAlchemy pattern / Pydantic pattern / FastAPI router pattern）写等价 Python。

#### D. 逐文件验证

每写完一个文件：

```bash
cd docdoku-plm-server-py && python -c "from app.<target_module> import <ClassName>"
```

失败 → 分析错误 → 修复 → 重试。最多 3 轮。

#### E. 全批验证

全批 20 个文件的 import 都通过后：

```bash
cd docdoku-plm-server-py && pytest tests/ -q --tb=short
```

#### F. 失败处理

```
pytest 失败：
  ├─ ImportError → 查 import 路径 → 修复 → 重跑(最多3轮)
  ├─ AssertionError → 可能是 relationship 断裂 → 检查 FK 引用 → 修复 → 重跑
  ├─ 3轮未能修复 → 标记本行为 ⚠️Stub → 继续下一批
  └─ 其他 → 暂停，展示错误，等用户决策
```

#### G. 更新 CSV

全批通过后，更新本批所有行的状态为"已完成"：

```csv
M-015,Model,product,P0A,已完成,...  # 旧: 待拆分
```

---

## 批次编组规则

1. 同域且同操作（待拆/待建）才打包
2. 每包 ≤20 行
3. 包内按 tracker CSV 原有顺序
4. 绝对禁止待拆和待建混包

---

## 进度报告格式

每批完成后输出：

```
BATCH DONE: P0A-product-01
  完成: 13/13 文件
  类型: Model 拆分
  全局进度: 91/523 (17.4%)
  耗时: 3m 24s
  下一批: P0A-product-02 (5 ✂️)
```

---

## 优先级切换确认

当执行完一个优先级（如 P0A 全部完成）准备进入下一个（P0B）时，暂停并报告：

```
P0A 阶段完成: 47/47 拆分通过, pytest 全绿
下一阶段: P0B (147 新建) — 确认继续？
```

用户说"继续"或"go" → 继续。不说话 → 等 30 秒后自动继续。

---

## 禁止行为

- ❌ 不读 Java 源码直接猜字段/逻辑
- ❌ 混包（拆+建放同一批）
- ❌ 跳过验证步骤
- ❌ 验证失败不修复直接往下走
- ❌ 修改已有代码的业务逻辑（只改 import 路径）
- ❌ 使用字符串形式 `secondaryjoin="and_(...)"` 代替 lambda — 字符串无法捕获模块级变量（如 Table 对象 `part_revision_tags`），SQLAlchemy 映射初始化时报 `failed to locate a name` 错误

---

## 拆分时的跨文件 relationship 规则（P0A regression 教训）

### 问题

拆分后各实体分散到不同文件，`relationship()` 中的 `secondaryjoin` 等参数若写成字符串形式：
```python
secondaryjoin="and_(foreign(Tag.workspace_id)==remote(part_revision_tags.c.tag_workspace_id), ...)"
```
SQLAlchemy 在评估该字符串时无法访问当前模块的变量（如 `part_revision_tags` Table 对象），导致 `InvalidRequestError: failed to locate a name`。

### 正确做法

1. **必须使用 lambda** 捕获当前模块内的 Table 对象和跨模块导入的类：
   ```python
   secondaryjoin=lambda: (Tag.workspace_id == part_revision_tags.c.tag_workspace_id)
                          & (Tag.label == part_revision_tags.c.tag_label)
   ```

2. **lambda 引用的外部类必须在文件底部懒导入**，避免循环导入：
   ```python
   # 文件末尾
   from app.models.part import Tag       # noqa: E402
   from app.models.common.workspace import Workspace  # noqa: E402
   ```

3. **`primaryjoin` 同理**：如果引用当前模块的 Table 对象，也必须用 lambda：
   ```python
   primaryjoin=lambda: PartIteration.workspace_id == part_iteration_binres.c.workspace_id)
   ```

4. **`relationship()` 的第一个参数用字符串没问题**（如 `"PartMaster"`），这些类名由 SQLAlchemy mapper registry 解析，不依赖模块作用域。
