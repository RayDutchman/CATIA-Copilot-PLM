# docs 目录重组实施计划

> **For agentic workers:** 本计划用于按 superpowers 规范整理 `docs/` 目录，消除 Agent 阅读歧义。步骤用 checkbox 跟踪。

**Goal:** 将散乱的 `docs/` 按「活跃 / 稳定参考 / 归档」三态分层，确立 `migration/loose-ends.md` 为迁移缺口唯一台账，重写 `DOCS_INDEX.md` 为通用文档地图。

**Architecture:** 纯 `git mv` 移动 + 索引重写，零内容删除，全部可 git 回溯。新增 `docs/migration/`（活跃迁移专题）与 `docs/superpowers/archive/{migration-process,handoffs}/`（施工期归档）。

**Tech Stack:** Markdown 文档 + git mv + grep 交叉引用修正。

## Global Constraints

- 用户已确认 4 项决策：中等力度（分层+归档）、loose-ends 为迁移唯一台账 REMINDERS 只引用、DOCS_INDEX 重写为通用地图、先出计划再执行。
- 第一优先级：**Agent 阅读时不产生歧义**。
- 全部用 `git mv`，禁止 delete+create（保留历史）。
- methodology.md 归入 migration/（前端迁移复用资产），**不**归档。
- tracker.csv 保留（迁移施工凭证），标注只读归档态。
- 不自动 git commit（等用户明确指示）。

---

## 目标结构

```
docs/
├── DOCS_INDEX.md          # 重写：通用文档地图 + Agent 阅读路由
├── CHANGELOG.md           # 活跃（不动）
├── REMINDERS.md           # 活跃（改：指向 migration/loose-ends，删重复迁移条目）
├── architecture/          # 稳定参考（不动内容）
├── reference/             # 稳定参考（不动）
├── setup/                 # 稳定参考（不动）
├── issues/                # 活跃（不动）
├── migration/             # 新增：迁移专题
│   ├── README.md             # 新建：三文件用途说明
│   ├── loose-ends.md         # ← migration-loose-ends.md
│   ├── methodology.md        # ← migration-methodology.md
│   └── tracker.csv           # ← migration-tracker.csv（只读归档）
└── superpowers/
    ├── plans/  specs/        # 未来新计划/设计
    └── archive/
        ├── plans/  specs/    # 已完成历史（不动）
        ├── handoffs/         # 新增
        │   └── handoff-2026-07-08.md
        └── migration-process/ # 新增：施工期工具文档
            ├── ai-execution-rules.md
            ├── batch-protocol.md
            ├── file-mapping.md
            ├── throw-matrix.md
            ├── migration-plan-complete.md
            ├── audit-report.md
            └── fastapi-migration-roadmap.md
```

---

## Task 1 — 迁移专题目录（活跃）
- [x] `mkdir -p docs/migration`
- [x] `git mv docs/migration-loose-ends.md docs/migration/loose-ends.md`
- [x] `git mv docs/migration-methodology.md docs/migration/methodology.md`
- [x] `git mv docs/migration-tracker.csv docs/migration/tracker.csv`
- [x] 新建 `docs/migration/README.md`：说明 loose-ends（剩余缺口台账，唯一事实来源）/ methodology（前端迁移复用）/ tracker.csv（已完成施工记录，只读）

## Task 2 — 施工期文档归档
- [x] `mkdir -p docs/superpowers/archive/migration-process docs/superpowers/archive/handoffs`
- [x] git mv 7 文件进 migration-process/：ai-execution-rules.md, batch-protocol.md, file-mapping.md, throw-matrix.md, migration-plan-complete.md, audit-report.md, superpowers/fastapi-migration-roadmap.md
- [x] `git mv docs/handoff-2026-07-08.md docs/superpowers/archive/handoffs/`

## Task 3 — 交叉引用修正（防断链）
- [x] grep 全 docs/ 找移动文件的引用（file-mapping 11 处、throw-matrix 7、migration-tracker 6、audit-report/methodology 4、migration-plan-complete 2、ai-execution-rules 3、batch-protocol 1）
- [x] 逐一更新为新路径
- [x] migration/loose-ends.md 内 `migration-tracker.csv` → `tracker.csv`（同目录）

## Task 4 — 重写 DOCS_INDEX.md
- [x] 删除过期语义（"唯一任务队列"、"AI 每次启动从 CSV 读待办"）
- [x] 三区文档地图：活跃 / 稳定参考 / 归档
- [x] 新增「Agent 阅读路由」：按场景（改 bug / 迁移收尾 / 查架构 / 查 API）给入口
- [x] 标注 architecture 两个 *-migration-plan 状态（gltf 已完成、conversion 待评审）

## Task 5 — REMINDERS.md 去重
- [x] 待办区删与 loose-ends 重复的 PathData/importer 明细，保留一行指针（路径 → migration/loose-ends.md）
- [x] 保留非迁移待办（3D 预览、Decimation、Windows 网络）

## Task 6 — architecture plan 状态标注
- [x] 在 DOCS_INDEX 标注两个 *-migration-plan 状态（文件头已有，仅索引层标注）

## Task 7 — 收尾
- [x] 更新 CHANGELOG.md（docs: 重组条目）
- [x] `git status` 核对全为 R（rename）非 D+A，确认历史保留
- [x] 不自动 commit
