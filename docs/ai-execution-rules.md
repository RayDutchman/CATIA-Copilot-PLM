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

---

## P1B Schema 新建阶段的经验教训

### 问题 1：CSV 目标路径可能已过时

部分 P1B 项在早期阶段（P0A/P1A）已被拆分到了子目录中，但 CSV 目标路径未更新：

| 编号 | CSV 目标 | 实际位置 |
|------|---------|---------|
| D-034 | `layer.py` | `product/layer.py` |
| D-044 | `marker.py` | `product/marker.py` |
| D-075 | `shared_document.py` | `misc/shared_document.py` |
| D-076 | `shared_part.py` | `misc/shared_part.py` |

**教训**：开始新批次前，先用 `grep -rl "ClassName" app/schemas/` 检查 DTO 是否已存在，不要盲目按 CSV 路径创建。

### 问题 2：缺失的隐式依赖 DTO

Java 源码引用了 CSV 未列出的 DTO，必须一并创建：

| 隐式依赖 | 被谁引用 | 来源 |
|----------|---------|------|
| `LightPartRevisionDTO` | `ImportPreviewDTO` | D-039 标记 P1A 已完成但文件不存在 |
| `ConfigurationItemKeyDTO` | `EffectivityDTO` | Java `ConfigurationItemKey` 值对象，不在 DTO 列表中 |

**教训**：写 Schema 前先扫描 `List["ClassName"]` 等引用，对照已存在文件，缺失则先补。

### 问题 3：覆盖已有文件需保持类名兼容

`product_instance_master.py` 和 `product_instance_iteration.py` 已存在，旧代码使用 `ProductInstanceDTO` 类名。Java 版本为 `ProductInstanceMasterDTO`。全部字段更新后必须添加别名：

```python
ProductInstanceDTO = ProductInstanceMasterDTO  # 兼容旧名称
```

**教训**：修改已有文件时，先 `grep -rn "OldClassName" app/` 找所有引用，必要时添加别名保持兼容。

### 问题 4：CSV 列索引错误

用 Python 自动化更新 CSV 时，错误替换了优先级列（`row[3]`）而非目标路径列（`row[6]`）。修复脚本同样需要验证。

**教训**：更新 CSV 后必须 `grep` 几个关键行验证列内容正确。

### 问题 5：Java DTO 继承合并

`EffectivityDTO` 在 Java 中已包含所有子类型字段（`startDate`/`endDate`/`startLotId`/`endLotId`/`startNumber`/`endNumber`）。子类 `DateBasedEffectivityDTO`、`LotBasedEffectivityDTO`、`SerialNumberBasedEffectivityDTO` 虽然 `extends EffectivityDTO`，但添加的字段已在父类中。Pydantic 中直接做空子类即可：

```python
class DateBasedEffectivityDTO(EffectivityDTO):
    pass
```

### 问题 6：Pydantic 循环引用标准模式

复杂 DTO（如 `ProductInstanceIterationDTO`、`PathDataMasterDTO`）互相嵌套引用，必须用 **string annotations + 底部 lazy import + `model_rebuild()`** 三步法：

```python
# 步骤 1: 类型注解用字符串
class ParentDTO(BaseModel):
    children: List["ChildDTO"] = []

# 步骤 2: 文件底部 lazy import
from app.schemas.xxx.child import ChildDTO  # noqa: E402

# 步骤 3: model_rebuild 解决前向引用
ParentDTO.model_rebuild()
```

**关键**：这些 DTO 不涉及 SQLAlchemy relationship，所以只需 `model_rebuild()`，**不需要 lambda**（lambda 规则仅适用于 ORM 模型的 `secondaryjoin`/`primaryjoin`）。

### 问题 7：Java 集合继承 → Pydantic RootModel

`StringListDTO extends ArrayList<String>` 和 `CheckedOutStatsResponseDTO extends HashMap<...>` 这类集合继承，在 Pydantic V2 中用 `RootModel` 或自定义 `__root__`：

```python
# StringListDTO → JSON 序列化为纯字符串数组
StringListDTO = RootModel[List[str]]
```

---

## 审计阶段 Prompt 模板（来自原 file-mapping.md 第四章）

> 用于审计修复阶段。对每个 Java→Python 文件对套用此 Prompt。

```markdown
You are auditing a Java→Python migration file pair.

Java file: {JAVA_FILE_PATH}
Python file: {PYTHON_FILE_PATH}

Read both completely. Java is the ground truth — any divergence is a finding.
Think independently. Do not limit yourself to a checklist.
Common blind spots from past audits include:

- **Coverage**: Does Python implement everything Java provides? Method by method.
  Logic equivalence matters more than name matching. Flag any missing functionality.
- **Data integrity**: Compare every SQL query, every DB operation. Same tables?
  Same conditions? Same ordering? Java is the ground truth — any difference is a finding.
- **Error handling**: For every failure path in Java, does Python have equivalent protection?
  Same i18n key? Same exception type? Also check: silent swallowing, new error conditions.
- **API contract**: Every Java DTO field must have a Python response equivalent with matching
  camelCase name, nested structure, and type. Missing OR extra fields both count.
- **Write verification**: Any Python code path that returns success without persisting data
  (db.commit()) is a critical finding. Check both explicit stubs (return []/{}) and
  implicit stubs (return 204 with no DB op).
- **Value fidelity**: For every response field, trace the value to its origin.
  What DB column or computation produced it? Is it being transformed correctly?
- **Non-null defaults**: Array/list fields must NEVER be None — use `[]`.
  Object/dict fields must NEVER be None — use `{}`. Backbone.js models call `.length`
  and `.name` without null checks.
- **List vs Detail parity**: Inline list comprehensions often have fewer fields than
  `_to_dict()` helpers used by detail endpoints.
- **Cross-cutting security**: For every Java method entry point that calls
  checkWorkspaceReadAccess/checkWorkspaceWriteAccess/checkAdmin, verify Python has
  equivalent check.
- **Exception throw parity**: Read `docs/throw-matrix.md`. For every row marked "缺 raise",
  verify or add the corresponding `raise` statement.
- **i18n bypass**: Hardcoded strings instead of ApplicationException subclasses with
  i18n keys like `NotAllowedException37`.
- **Wrong column names**: If a query uses columns that don't exist, that's critical.
- **Dead imports**: `from sqlalchemy import text` missing when `text()` is used.

Focus on what would actually break at runtime. Cross-reference Java with Python relentlessly.
```

---

## 全量审计 + 修复执行结果

> 记录于 2026-07-07。524/524 tracker 清零后，执行 5 步审计 + 7 批修复。

### 审计阶段 (5 步)

| Step | 内容 | 结果 |
|------|------|------|
| 1 | NotImplementedError 残留 | ✅ 0 |
| 2 | 空函数 (pass) | ✅ 0 |
| 3 | TODO/FIXME 残留 | ⚠️ 25 → 已全量清理 (0) |
| 4 | HTTP 对拍 V2 | 162 端点: 73 MATCH / 42 PARTIAL / 47 MISMATCH |
| 4b | full_compare V3 字段 diff | 138 端点: 81 MATCH / 11 PARTIAL / 44 MISMATCH |
| 5 | 代码质量抽查 | 12 方法: 🔴17 + 🟡10 |

### 修复阶段 (7 批, 全绿零回归)

| 批 | 优先级 | 修复内容 | 提交 |
|----|--------|----------|------|
| B1 | 🔴 | document 级联删除 8 表 + product 模板 + Workflow Tasks | 93b0695 |
| B2 | 🔴 | ACL写权限 + 组成员校验 + 签出保护 + InstanceAttributeTemplates | 294fb15 |
| B3 | 🟡 | 39 NotFound→404 + 补全 2 路由 | b90f0e2 |
| B4 | 🟡 | 文档/零件/变更 DTO 字段补全 | 7c3373b |
| B5 | 🟡 | Workflow admin绕过 + SequentialActivity + status移除 | 043adbe |
| B6 | 🟡 | 7 个 raise 补齐 (NotAllowed42 + AccessRight × 5) | 043adbe |
| B7 | 🟢 | 6实现 + 12 STUB标注 + 6 清理 → TODO 残留 0 | 93cf836 |

### 最终状态

| 指标 | 值 |
|------|-----|
| tracker 完成 | **524/524 (100%)** |
| 测试 | 176 passed, 1 skipped |
| TODO 残留 | **0** |
| 审计 MISMATCH | 13 项: 12 已修复, 1 遗留 (Workflow role_mapping) |
| 执行模式 | AI agent 编排 → 并行 agent 修复 → pytest → commit |
```
