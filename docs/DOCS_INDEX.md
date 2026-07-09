# 文档索引（Agent 必读）

> **这是 `docs/` 的唯一入口。** Agent 启动时先读本文件，判断该读哪些文档。
> 文档按生命周期分三态：**🟢 活跃**（持续更新）、**📘 稳定参考**（按需查阅）、**🗄️ 归档**（历史追溯）。

---

## 一、按场景的 Agent 阅读路由

| 你要做的事 | 先读 |
|-----------|------|
| **修 bug / 排查问题** | `issues/known-issues.md` → 对应 `architecture/*.md` |
| **继续后端迁移收尾** | `migration/loose-ends.md`（剩余缺口唯一台账）→ `migration/methodology.md`（方法论） |
| **了解当前待办/阻塞** | `REMINDERS.md` |
| **查系统架构 / 容器 / CAD 转换** | `architecture/*.md` |
| **查 REST API / 认证 / 用户手册** | `reference/*.md` |
| **部署 / 运维** | `setup/*.md` |
| **做前端迁移（Backbone→React）** | `migration/methodology.md`（复用后端迁移方法论） |
| **查迁移施工历史** | `superpowers/archive/migration-process/*` |

---

## 二、🟢 活跃文档（每次会话/任务后维护）

| 文件 | 用途 | 更新时机 |
|------|------|---------|
| `CHANGELOG.md` | 变更日志（feat/fix/chore/docs） | 每批任务完成后追加 |
| `REMINDERS.md` | 跨领域滚动待办 + 阻塞 + 已解决 | 每批任务完成后同步 |
| `migration/loose-ends.md` | **后端迁移剩余缺口唯一台账**（~59 处） | 修复某项后勾选 |
| `issues/known-issues.md` | 已知 Bug 追踪 | 发现/修复 bug 时 |

> ⚠️ **迁移已完成**：Payara→FastAPI 后端迁移主体已 100% 完成（`migration/tracker.csv` 523/523），Payara 生产链路已被绕过。**不要**再把 `tracker.csv` 当作待办队列——剩余功能缺口只看 `migration/loose-ends.md`。

---

## 三、📘 稳定参考（按需查阅，不常更新）

| 目录/文件 | 用途 |
|-----------|------|
| `architecture/containers.md` | 容器架构、端口、数据卷 |
| `architecture/3d-visualization.md` · `3d-preview-pipeline.md` | 3D 预览 / CAD 转换机制 |
| `architecture/assembly-position.md` | 装配体位置 / cadInstances |
| `architecture/data-management.md` | 数据管理、vault 结构 |
| `architecture/gltf-migration-plan.md` | STEP→glTF 迁移方案（🟢 **已完成**，实施结果见 3d-preview-pipeline.md） |
| `architecture/conversion-service-python-migration-plan.md` | 转换服务 Java→Python 方案（🟡 **待评审，未实施**） |
| `reference/rest-api.md` | REST API 参考 |
| `reference/auth-and-accounts.md` | 认证与账号 |
| `reference/user-manual.md` · `3d-preview-tuning.md` | 用户手册 / 3D 调优 |
| `setup/deployment-wsl2-docker.md` · `linux-ops-guide.md` | 部署与运维 |
| `migration/methodology.md` | 迁移方法论（7 维审计 + 文件映射法，前端迁移可复用） |
| `migration/README.md` | 迁移专题目录说明 |

---

## 四、🗄️ 归档（历史追溯，勿作为当前依据）

| 目录 | 内容 |
|------|------|
| `migration/tracker.csv` | 523 条后端迁移施工记录（只读，已 100% 完成） |
| `superpowers/archive/migration-process/` | 施工期工具文档：ai-execution-rules、batch-protocol、file-mapping、throw-matrix、migration-plan-complete、audit-report、fastapi-migration-roadmap |
| `superpowers/archive/handoffs/` | 会话交接快照（handoff-2026-07-08.md 等） |
| `superpowers/archive/plans/` · `specs/` | 已执行完毕的阶段计划与设计文档 |

> 归档文档顶部均有 🗄️ banner，文中 `docs/xxx.md` 旧路径可能已失效，以本索引为准。

---

## 五、superpowers 规范目录

| 目录 | 用途 |
|------|------|
| `superpowers/plans/` | **新**实现计划存放处（`YYYY-MM-DD-<feature>.md`，writing-plans skill 规范） |
| `superpowers/specs/` | **新**设计文档存放处 |
| `superpowers/archive/` | 上述执行完毕后归档至此 |

---

## 六、文档维护规则（会话收尾必做）

完成任务后按 `.opencode/instructions.md` 要求：
1. 更新 `CHANGELOG.md`（当天日期条目）
2. 更新 `REMINDERS.md`（已解决移出待办、新增阻塞）
3. 同步相关文档：改架构→`architecture/`；修 bug→`issues/known-issues.md`；迁移收尾→`migration/loose-ends.md`（勾选）
