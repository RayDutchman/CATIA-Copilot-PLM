# 迁移专题（migration/）

> 本目录聚合与 **Payara(Java) → FastAPI(Python) 后端迁移** 相关的**活跃**文档。
> 施工期的产线工具文档（执行规则、审计报告、路线图等）已归档至 `../superpowers/archive/migration-process/`。

---

## 文件用途（避免歧义）

| 文件 | 定位 | 状态 | 何时读/写 |
|------|------|------|-----------|
| `loose-ends.md` | **迁移剩余缺口的唯一台账** | 活跃 | 规划/执行迁移收尾时读；修复某项后在此勾选 |
| `methodology.md` | 迁移方法论（7 维审计 + 文件映射法） | 复用参考 | 前端迁移（Backbone→React）复用时读 |
| `tracker.csv` | 523 条后端迁移施工记录 | **只读归档** | 查历史；已 100% 完成，非活跃任务队列 |

---

## 重要区分

- **`loose-ends.md` vs `REMINDERS.md`**：`loose-ends.md` 是迁移缺口的结构化专题台账（唯一事实来源）；`REMINDERS.md` 是跨领域滚动看板，对迁移仅保留一行指针，不重复明细。
- **`tracker.csv` 已完成**：它追踪的是 Model/DAO/Service 层文件迁移（523/523 完成），**不是**待办队列。REST 路由层的剩余缺口见 `loose-ends.md`。
