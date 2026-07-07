# 文档索引（AI 必读）

> AI agent 启动时先读本文件，了解哪些文档需要读、哪些需要更新、哪些已过时。

---

## 一、持续更新文件（每次会话/每批任务后必更新）

| 文件 | 用途 | 更新时机 |
|------|------|---------|
| `docs/CHANGELOG.md` | 变更日志（feat/fix/chore/docs） | 每批任务完成后追加 |
| `docs/REMINDERS.md` | 待办 + 已知问题 + 已解决 | 每批任务完成后同步 |
| `docs/migration-tracker.csv` | **唯一任务队列**（523 行） | 每批任务完成后更新状态 |
| `docs/audit-report.md` | 验收审计报告（5步） | 审计完成后更新 |

---

## 二、AI 执行规则（任务时必读）

| 文件 | 用途 | 说明 |
|------|------|------|
| `docs/ai-execution-rules.md` | **AI 自驱动行为规则** | 定义了执行循环、分批评审、并行策略、验证步骤 |
| `docs/batch-protocol.md` | 产线设计概览（给人看） | 配合 ai-execution-rules.md 使用 |
| `docs/migration-tracker.csv` | **唯一任务队列+进度** | AI 每次启动从 CSV 读待办、完成后写回 |
| `docs/file-mapping.md` | 基础设施映射参考（22 项）+ 文件夹结构 | 按需 |
| `docs/ai-execution-rules.md` | **AI 自驱动行为规则 + 7 维审计 Prompt + 全量审计结果** | 任务时必读 |
| `docs/throw-matrix.md` | 异常抛出对照表 | 第 7 维审计（Exception throw parity）依据 |

> ✅ **成功经验**：`ai-execution-rules.md` + `migration-tracker.csv` 组合已证明可让 AI 无人干预下自驱执行 523 行迁移。

---

## 三、方法论与参考（需要时查阅，不常更新）

| 文件 | 用途 | 更新频率 |
|------|------|---------|
| `docs/migration-methodology.md` | **迁移方法论（最终版）** | 低（方法论定型后少改） |
| `docs/superpowers/fastapi-migration-roadmap.md` | 原始路线图（含阶段依赖+经验教训） | 低（作为历史参考保留） |
| `docs/migration-plan-complete.md` | 迁移计划（含完成度评估） | ⚠️ 内容已过时，待更新 |
| `docs/architecture/*.md` | 容器架构/CAD转换/数据管理 | 按需（架构变更时） |
| `docs/reference/*.md` | REST API/认证/用户手册 | 按需 |
| `docs/setup/*.md` | 部署运维操作手册 | 按需 |
| `docs/issues/known-issues.md` | 已知 Bug 追踪 | 发现/修复 bug 时 |

---

## 四、已过时文件（归档或删除候选）

| 文件 | 原因 | 建议 |
|------|------|------|
| `docs/superpowers/plans/*.md` (8个) | 2026-07-04~06 阶段计划，执行完毕 | 归档到 `docs/superpowers/archive/` |
| `docs/superpowers/specs/*.md` (7个) | 2026-07-04~06 设计文档，执行完毕 | 归档到 `docs/superpowers/archive/` |
| `docs/batch-protocol.md` | 内容已被 ai-execution-rules.md 覆盖 | 保留作为给人看的概览 |

---

## 五、推荐 AI 阅读顺序

当用户说"执行迁移"或"开始修复"时，AI 按此顺序读：

```
1. docs/ai-execution-rules.md      ← 怎么执行
2. docs/migration-tracker.csv      ← 做什么（任务队列）
3. docs/REMINDERS.md               ← 当前待办/阻塞
4. docs/file-mapping.md L108-136   ← 审计 prompt 模板
5. docs/throw-matrix.md            ← 异常对齐参考
```

如果涉及架构变更：额外读 `docs/architecture/*.md`。
如果涉及 i18n/异常：额外读 `docs/migration-methodology.md`。

---

## 六、文件依赖关系

```
docs/batch-protocol.md (给人看)
  └─ docs/ai-execution-rules.md (给AI看)
       ├─ docs/migration-tracker.csv (任务队列)
       ├─ docs/file-mapping.md (审计模板)
       ├─ docs/throw-matrix.md (异常参考)
       ├─ docs/CHANGELOG.md (写)
       ├─ docs/REMINDERS.md (写)
       └─ docs/audit-report.md (写)

docs/migration-methodology.md (方法论总纲)
  └─ docs/superpowers/fastapi-migration-roadmap.md (历史路线图)
