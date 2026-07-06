# 自动化迁移产线设计

> **你只需要两条指令**：启动 + 确认阶段切换。其余全自动。
> AI 执行规则详见 `docs/ai-execution-rules.md`。

---

### 每批内部怎么做（AI 自决策，你不需要管）

AI 自主决定用并行还是串行：20 个 Java 源文件可拆成 4 组 `explore` subagent（免费模型）并行读 → 汇总 context → 1 个 agent 串行写 Python（避免文件冲突）→ 逐文件 import 验证 → 最后跑一次 pytest。详细规则见 `docs/ai-execution-rules.md`。

```
你: "执行迁移"
        │
        ▼
┌───────────────────────────────────────────────────┐
│                                                     │
│  AI 读 docs/migration-tracker.csv                   │
│  ↓                                                   │
│  按优先级排序(P0A→P0B→P1A→...) + 同域编组(≤20行/批)   │
│  ↓                                                   │
│  ┌─ 批1: 读Java源码 → 拆/写Python → import验证 ─┐   │
│  │  └─ 失败? → 自修复(最多3轮) → 仍失败 → Stub   │   │
│  │  └─ 通过? → pytest全量 → 更新CSV → 下一批 ───┘   │
│  │                      ↓                            │
│  │              打印 "BATCH DONE"                    │
│  │                      ↓                            │
│  │              自动开始下一批                        │
│  │                      ↓                            │
│  │              (循环, 直到阶段结束)                   │
│  └──────────────────────────────────────────────     │
│                      ↓                               │
│  阶段切换(P0A↛P0B): 暂停报告, 等你说"继续"             │
│                      ↓                               │
│  全部523行完成: 报告 "迁移完成"                        │
│                                                     │
└───────────────────────────────────────────────────┘
```

---

## 你只做三件事

| 时机 | 操作 | 耗时 |
|------|------|------|
| **启动** | 一句话："执行 P0A" | 5 秒 |
| **阶段切换** | AI 暂停展示进度，你说"继续" | 2 秒 |
| **自修复失败** | AI 暂停展示错误，你决策"跳过/手动修" | 1-5 分钟 |

其余时间 AI 自己在跑，你可以切走干别的。

---

## 你的代码为什么不会白写

```
当前 9 个大文件（如 models/part.py, 476行）
         │
         │  AI 的拆分操作：
         │  1. 定位到 class PartMaster(Base)
         │  2. 复制 → models/product/part_master.py
         │  3. 改内部 import 路径
         │  4. 改外部引用方 import 路径
         │  5. 验证通过 → 继续下一个 class
         ▼

拆分后: 167 个独立小文件
  models/product/part_master.py      ← 逻辑一字未改，只是搬家
  models/product/part_revision.py    ← 同上
  models/product/part_iteration.py   ← 同上
  ...
```

唯一改动 = `from models.part import X` → `from models.product.part_master import X`。不是重写。

---

## 阶段执行顺序

```
P0A (47✂️)  Model拆分     ← 先拆已有的, ~3天
   ↓ pytest全绿
P0B (147🆕) Model新建     ← 再补缺失的, ~4天
   ↓
P1A (63✂️)  Schema拆分    ← ~2天
P1B (62🆕)  Schema新建    ← ~3天
   ↓
P2A (6✂️)   Service拆分   ← ~1天
P2B (68🆕)  Service新建   ← ~4天
   ↓
P3B (23🆕)  Router+资源   ← ~2天
P4B (29🆕)  WS+Ext       ← 低优先级
```

每个 ↗ 处 AI 暂停，等你确认。

---

## 相关文件

| 文件 | 谁看 | 内容 |
|------|------|------|
| `docs/batch-protocol.md` | **你** | 本文档，设计方案概览 |
| `docs/ai-execution-rules.md` | **AI** | 自驱动执行规则 |
| `docs/migration-tracker.csv` | **双方** | 唯一任务队列+进度数据 |
| `docs/migration-plan-complete.md` | **你** | 完整迁移计划（含评估） |
| `docs/file-mapping.md` | AI(审计阶段) | 7 维审计 prompt 模板 |
| `docs/throw-matrix.md` | AI(执行阶段) | 异常对齐参考 |
