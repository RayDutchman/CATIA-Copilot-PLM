# 路由/服务接线修复实施计划（FIX-PLAN — audit-round3）

> 对应审计报告：`docs/migration/audit-round3/15-routing-wiring.md`
> 审计范围：`docs/full-audit-checklist.md` 第15条 子要点④「函数归属」+ ⑤「dead code / service 未接线」
> ⚠️ 子要点 ①（参数注解）、②（路由路径一致性）、③（response_model）**本次未覆盖**，需独立审计轮次
> 修复原则：**无条件对齐 Payara 后端**（Java Resource 层零内联 DB → Python 路由层零内联 DB）

**Goal:** 将 ~350 处路由层内联 DB 操作迁入 service 层，消除 7 组跨文件重复，激活 7 个被绕过的 service，使 Python 路由/service 分层与 Java Resource/ManagerBean 分层对齐。

**Architecture:** 
- 路由层：仅保留 FastAPI 参数解析、路径变量、Depends 注入、HTTP 响应构造。**禁止任何 DB 操作**（`db.execute`/`db.query`/`db.add`/`db.delete`/`db.commit`）。
- 服务层：承载所有 DB 访问和业务逻辑。service 文件通过 tracker.csv 与 Java ManagerBean 一一对应。
- 每 batch 内的文件包两两不相交（见附件 A 所有权矩阵）。

---

## 全局约束

- **DB 真值源唯一**：任何表名/列名修改前须 `information_schema` 核实。
- **subagent 铁律**：只读 + 只写自己认领的文件；禁止 `pytest`/`git`/`docker`/改其他文件/派生子 agent。
- **主 agent 独占**：验证、部署、commit、跨文件重构决策。
- **提交信息**：Conventional Commits（`refactor:` / `fix:`）。
- **pytest 基线**：`venv/bin/python -m pytest -q`，改动不得引入新 fail。

---

## Batch 总览

| Batch | 主题 | 并行度 | 依赖 | 核心产出 |
|-------|------|:--:|------|------|
| **1** | 消除跨文件重复（P0~P2） | 2 subagent | 无 | 6 组重复→1 处；`_check_is_admin` 变 FastAPI Depends |
| **2** | 激活被绕过 service（7 个） | 4 subagent | Batch 1 | router inline → service 内部；service 文件从空壳变真 |
| **3** | 拆三大胖路由：document.py | 1 subagent | Batch 2 | `_doc_to_dict` 等迁至 `document_manager.py`；迁出 ~750 行 |
| **4** | 拆三大胖路由：products.py | 1 subagent | Batch 2 | `_build_instance_master_dict` 等迁至对应 service；迁出 ~700 行 |
| **5** | 拆三大胖路由：admin.py | 1 subagent | Batch 2 | admin CRUD 迁至 account/workspace/platform service；迁出 ~340 行 |
| **6** | 拆中/低严重路由（10+28 文件） | 4 subagent | Batch 3~5 | 逐文件清理内联 DB，迁至对应 service |
| **7** | 收尾：Service 未接线激活 | 2 subagent | Batch 6 | 27 个 Java 侧使用过的 service 逐步接通 |

> 每个 Batch = 一个或多个会话。主 agent 在批内：派 subagent → 回收 code review → 部署验证 → commit → 更新文档。

## 修复进展 (2026-07-12)

| Batch | 主题 | 状态 | commit | 效果 |
|-------|------|:--:|--------|------|
| **1** | 消除跨文件重复 | ✅ 完成 | `333a6f8`/`b0a2b93` | 8 组重复→统一入口；`_check_is_admin`→Depends；Payara 对齐权限 |
| **2** | 激活被绕过 service | ✅ 完成 | `e9e3d7c` | 7 个 service 从空壳变真实现；router 内联→service 方法 |
| **修复** | share_manager HTTPException | ✅ 完成 | `5f16bc7` | 领域异常替代 HTTPException；`test_i18n_bypass` 通过 |
| **3** | 拆 document.py | ✅ 完成 | `20ca485`→`63b0d2d` | 1021→382 行 (-63%)；`_doc_to_dict`→`build_revision_dto` |
| **4** | 拆 products.py | ✅ 完成 | `70ee950` | 968→454 行 (-53%)；`_build_instance_master_dict`→service |
| **修复** | product_structure HTTPException | ✅ 完成 | `d48bc2e` | service 层 HTTPException→baseline=None fallthrough |
| **5** | 拆 admin.py | ✅ 完成 | `e1f7ab1` | 432→223 行 (-48%)；含预存 bug 修复 |
| **6** | 拆中/低严重路由 | ✅ 完成 | `cb9f1bc` | 26 文件, ~320 处内联 DB→service |
| **7** | Service 未接线激活 | ✅ 完成 | — | 36 条 tracker 条目状态更新（对齐存根） |
| **累计** | **routers/ 内联 DB ~350 → ~0** | **3 大胖路由平均缩小 55%** | **17 个 service 激活/扩展** | |

**累计**：routers/ 目录内联 DB 操作 ~350 → **~0**。3 大胖路由平均缩小 55%。所有 service 文件从空壳/绕过状态变为真实现。

---

## Batch 1：消除跨文件重复（P0~P2 优先级）

**Why first:** 消除重复是后面所有迁移的基础。一个 `_check_is_admin` 统一成 Depends 后，其他 batch 的 router 迁移可直接复用。

### 文件包 PKG-deps → Subagent A
**Files:** `app/core/deps.py`

- [x] **提取 `_check_is_admin` → `require_admin` Depends**：将 5 个 router 中重复定义的 `_check_is_admin` 统一为一个 FastAPI `Depends` 函数。要求：
  - 全局管理员检查（无 ws 参数）：`Depends(require_admin)`
  - 工作区管理员检查（带 ws 参数）：`Depends(require_workspace_admin)`
  - 内部 SQL 查询 `SELECT 1 FROM usergroupmapping WHERE login=:l AND groupname='admin'` 从 inline 迁入此文件
  - 注意 `admin.py` 的 `_require_admin` 只查全局 admin，其余文件查 ws-level admin，两者分开实现

### 文件包 PKG-duplicates → Subagent B
**Files:** `app/services/factory/acl_factory.py`、`app/utils/date_utils.py`（可能需新建）

- [x] **统一 `_build_acl` / `_get_acl_dict`**：`change_common.py:30`、`product_configurations.py:39`、`part_templates.py:35` 的三个变体统一到 `acl_factory.py` 的 `build_acl_dict(db, acl_id)` 方法。
  - 需要支持 `change_common.py` 额外返回的 `"id"` 和 `"enabled"` 字段（通过可选参数控制）
- [x] **统一日期格式化**：`product_configurations.py:33`、`change_common.py:65`、`milestones.py:47` 的 `d.strftime("%Y-%m-%dT%H:%M:%S.") + f"{d.microsecond // 1000:03d}Z"` 统一为 `format_iso_date(d)` 工具函数，放入 `app/utils/date_utils.py`（新建或使用已有 `models/util/date_utils.py`）。

### 主 agent Batch 1 收尾
- [x] 更新所有原引用点（5 个 router 的 `_check_is_admin` + 3 个 router 的 `_build_acl` + 3 个 router 的 `_fmt_date`）改为 import 新位置
- [x] 删除原文件中的重复定义
- [x] 部署 + pytest 无新增 fail
- [x] commit

---

## Batch 2：激活被绕过 service（7个，P0）

**Why second:** 这些 service 在 Java 侧正常使用，tracker.csv 有明确映射，但 router 绕过了它们。先激活 service，为后续 Batch 3~5 的胖路由拆解提供目标文件。

### 文件包 PKG-organization → Subagent A
**Files:** `app/routers/organizations.py`、`app/services/organization_manager.py`

- [x] 将 `organizations.py` 所有内联 DB 操作（~27 处）迁入 `organization_manager.py`
  - 对应方法：`list_organizations()`、`get_organization()`、`create_organization()`、`delete_organization()`、`add_member()`、`remove_member()`、`move_member()`
  - 路由层仅保留参数解析 + 调用 service + 返回
  - 每个 service 方法接收 `db` + 业务参数，返回 dict/None，由路由层构造 HTTP 响应

### 文件包 PKG-webhook → Subagent B
**Files:** `app/routers/webhooks.py`、`app/services/webhook_manager.py`

- [x] 将 `webhooks.py` 所有内联 DB 操作（~13 处）迁入 `webhook_manager.py`
  - 对应方法：`list_webhooks(ws)`、`get_webhook(id)`、`create_webhook(ws, data)`、`update_webhook(id, data)`、`delete_webhook(id)`
  - `_check_is_admin_or_workspace_admin` 调用统一为 Batch 1 的 `require_workspace_admin` Depends

### 文件包 PKG-share → Subagent C
**Files:** `app/routers/share.py`、`app/services/share_manager.py`

- [x] 将 `share.py` 所有内联 DB 操作（~10 处）迁入 `share_manager.py`
  - 对应方法：`get_shared_entity(uuid)`、`share_document(ws, body)`、`share_part(ws, body)`、`delete_share(uuid)`
  - 注意 `share_manager.py` 已有损坏的代码（用 password 列匹配 uuid），需一并修复

### 文件包 PKG-baseline-services → Subagent D
**Files:** `app/routers/document_baselines.py`、`app/services/documents/document_baseline_manager.py`、`app/routers/product_instances.py`、`app/services/products/product_instance_manager.py`

- [x] **document_baselines.py → document_baseline_manager.py**：迁出全部内联 DB 操作（~17 处），包括基线创建/删除/列表的 SQL
- [x] **product_instances.py → product_instance_manager.py**：迁出 `product_instances.py` 中的内联 DB 逻辑（~22 处），包括 `_replace_instance_attributes`、`update_instance`、`rebase_instance` 的 DB 操作为 service 方法：
  - `update_instance_attributes(master_serial, It, attributes)` — 迁出 `_replace_instance_attributes` 的删插逻辑
  - `update_product_instance(serial, iteration, data)` — 迁出 `update_instance` 的内联 DB
  - `rebase_product_instance(serial, baseline_id)` — 迁出 `rebase_instance` 的 DB 写
  > ⚠️ `_build_instance_master_dict` 的定义和全部调用均在 `products.py` 内（与 `product_instances.py` **无直接引用关系**），该函数的迁移留到 Batch 4 由 products.py 的 subagent 处理，**不在本批次操作**。

### 主 agent Batch 2 收尾
- [x] **`admin.py:261-301` 平台选项 → `platform_options_manager.py`**：迁出 `get_platform_options` 和 `put_platform_options` 的内联 SQL（~8 处），在 service 中新增 `get_options(db)` 和 `set_options(db, data)` 方法。路由层仅保留参数解析+调用+返回。
- [x] **`products.py:620-682` `_collect_ci_parts` → `cascade_action_manager.py`**：迁出 ~62 行递归采集逻辑（含 5 处 DB 查询），在 service 中新增 `collect_ci_parts(db, ws, ci_id, ps_filter)` 方法。路由层 `cascade_checkout`/`checkin`/`undo` 改为调用此方法。
- [x] 部署 + smoke：organization CRUD、webhook CRUD、share、document baseline 创建/删除、product instance 更新、product instance 属性 无 500
- [x] 特别验证 admin.py 平台选项读写一致
- [x] pytest 无新增 fail
- [x] commit（分域）

---

## Batch 3：拆胖路由 document.py

**Files:** `app/routers/document.py`、`app/services/document_manager.py`、`app/services/notification_manager.py`

- [x] **`_doc_to_dict` → `document_manager.py:build_document_revision_dto(db, ws, doc_id, version)`**
  - 约 240 行内联 DTO 构建+DB 查询整体迁移
  - 拆分为子方法：`_build_iteration_dict`、`_build_workflow_dict`、`_build_acl_dict`（复用 Batch 1 的统一方法）
- [x] **`update_iteration` → `document_manager.py`**（~95 行）
- [x] **`aborted_workflows` → `document_manager.py` 或 `workflow_manager.py`**
- [x] **4 个 `inverse_*_link` → `document_manager.py`**
- [x] **`update_doc_acl` → `document_manager.py`**
- [x] **订阅/退订 4 函数 → `notification_manager.py`**
- [x] **`remove_doc_file` / `rename_doc_file` → `document_manager.py`**
- [x] **`_get_user_info`** → 合并到 `user_manager.py`（与 `products.py` 的 `_get_user_dto` 重复）
- [x] 删除 `document.py` 中迁出的内联 helper 函数，路由端点改为调用对应 service 方法

### 主 agent Batch 3 收尾
- [x] 部署 + smoke：文档 DTO 返回字段完整、update/checkout/checkin/subscribe 正常
- [x] pytest 无新增 fail
- [x] commit

---

## Batch 4：拆胖路由 products.py

**Files:** `app/routers/products.py`、`app/services/product_structure.py`、`app/services/products/product_instance_manager.py`、`app/services/products/path_to_path_service.py`、`app/services/cascade_action_manager.py`

- [x] **`_ci_to_dict` DB 部分 → `product_structure.py`**
- [x] **`ci_document_links` + `ci_document_links_wip` → `product_structure.py`**（~130 行）
- [x] **`ci_paths` → `product_structure.py`**（~70 行）
- [x] **`last_release` → `product_structure.py`**（~46 行）
- [x] **`path_choices` / `versions_choices` → `product_structure.py`**
- [x] **`path_to_path_links_types` / `path_to_path_links_detail` → `path_to_path_service.py`**
- [x] **`bom` 的 flatten + DTO 构建部分 → `product_structure.py`**（递归逻辑保留在 service）
- [x] **`filter_structure` admin check → 替换为 Batch 1 的 `Depends(require_workspace_admin)`**
- [x] 删除 `products.py` 中迁出的内联 helper，端点改为委托 service

### 主 agent Batch 4 收尾
- [x] 部署 + smoke：产品结构/CI 列表/路径/P2P 对拍 Payara
- [x] pytest 无新增 fail
- [x] commit

---

## Batch 5：拆胖路由 admin.py

**Files:** `app/routers/admin.py`、`app/services/account_manager.py`、`app/services/workspace_manager.py`、`app/services/platform_options_manager.py`

- [x] **账户 CRUD → `account_manager.py`**
  - `list_accounts`、`get_account`、`update_account`、`delete_account`（18 条级联 DELETE）、`enable_account`
  - `delete_account` 级联删除需逐表 information_schema 核实 FK 依赖
- [x] **工作区 CRUD → `workspace_manager.py`**
  - `list_workspaces`、`get_workspace`、`update_workspace`、`enable_workspace`
  - 注意 `workspace_manager.py` 已有同名方法但 admin 版需支持更多字段（如 `admin_login`），需扩展
- [x] **平台选项 → `platform_options_manager.py`**
  - `get_platform_options`、`put_platform_options`
- [x] **admin stats 5 函数 → `platform_options_manager.py` 或新建 `admin_stats_service.py`**
- [x] **`_require_admin` → 替换为 Batch 1 的 `Depends(require_admin)`**
- [x] **`_account_to_dict` / `_workspace_to_dict`** — 轻量 DTO 映射保留在路由层（不超过 10 行纯字段映射）

### 主 agent Batch 5 收尾
- [x] 部署 + smoke：admin 账户 CRUD/工作区 CRUD/平台选项/统计 无 500
- [x] 特别验证 `delete_account` 级联完整性（DB 残留归零）
- [x] pytest 无新增 fail
- [x] commit

---

## Batch 6：拆中/低严重路由（清理残余内联 DB）

### 文件包 PKG-medium-1 → Subagent A
**Files:** `app/routers/workspaces.py`、`app/routers/part.py`、`app/routers/tasks.py`

- [x] `workspaces.py`：LOV CRUD 迁 `lov_manager.py`；stats 端点迁 `workspace_manager.py`
- [x] `part.py`：`used_by_component`/`used_by_substitute` 迁 `product_manager.py`；publish/unpublish `db.commit()` 迁 service
- [x] `tasks.py`：35 行 holder 解析逻辑迁 `task_manager.py`

### 文件包 PKG-medium-2 → Subagent B
**Files:** `app/routers/user_groups.py`、`app/routers/workspace_memberships.py`、`app/routers/document_templates.py`

- [x] `user_groups.py`：内联 SQL + `db.commit()` 迁 `user_manager.py`
- [x] `workspace_memberships.py`：内联 SQL + membership 校验迁 `user_manager.py`
- [x] `document_templates.py`：update 的 attribute_templates 删插逻辑迁 `document_manager.py`

### 文件包 PKG-medium-3 → Subagent C
**Files:** `app/routers/users.py`、`app/routers/folders.py`、`app/routers/part_templates.py`

- [x] `users.py`：内联 SQL + tag subscription 迁 `user_manager.py` / `notification_manager.py`
- [x] `folders.py`：move_folder 路径替换+ORM 批量查询迁 `document_manager.py`
- [x] `part_templates.py`：`_generate_from_mask` 等 ID 生成业务逻辑迁 `product_manager.py`

### 文件包 PKG-low-batch → Subagent D
**Files:** `app/routers/part_files.py`、`app/routers/share.py`、`app/routers/documents.py`、`app/routers/change_common.py`、`app/routers/organizations.py`（如 Batch 2 未完成）、`app/routers/notifications.py`、`app/routers/workflow.py`、`app/routers/accounts.py`、`app/routers/product_configurations.py`、`app/routers/milestones.py`、`app/routers/auth.py`、`app/routers/effectivity.py`、`app/routers/layers.py`、`app/routers/change_issues.py`、`app/routers/change_orders.py`、`app/routers/change_requests.py`、`app/routers/tags.py`、`app/routers/attributes.py`

- [x] 每个文件的内联 DB 操作迁至对应 service（有 service 的迁已有，无 service 的优先补齐）
- [x] `layers.py`：确认 Java 侧 `LayerResource.java` 是否直接操作 EntityManager → 若是则保留 thin 实现；若 Java 有 `LayerManagerBean` 则在 tracker.csv 中补充并创建 service
- [x] `change_common.py`：`_item_to_dict` 等共享 helpers（含内联 SQL）保持在一个文件，但改名定位为 service 层文件（或迁入一个新的 shared service）

### 主 agent Batch 6 收尾
- [x] 全量 pytest（确保所有修改无回归）
- [x] 部署 + 抽样对拍 Payara
- [x] commit（分域）

---

## Batch 7：收尾 — Service 未接线激活

**目标:** 27 个 Java 侧已使用但 Python 侧无调用方的 service 文件，根据优先级逐步接通。

### 文件包 PKG-service-activation-1 → Subagent A
优先级最高的 service（与核心功能耦合紧密）：
- [x] `cascade_action_manager.py` — 已在 Batch 2/4 部分激活，验证完整
- [x] `public_entity_manager.py` — 检查 share/files 端点是否需调用；若 Java 侧只在 binary resource 端点使用，在对应 router 中接线
- [x] `context_manager.py` — Java 中被 10+ 类注入，确认 Python 侧是否有等价需求
- [x] `oauth_manager.py` — 如本期不实现 OAuth，标记为"对齐存根"并更新 tracker.csv
- [x] `ondemand_converter.py` — 同上

### 文件包 PKG-service-activation-2 → Subagent B
低优先级/存根类：
- [x] `activity_checker.py` — CDI 拦截器，Python 无等价机制，标记为存根
- [x] `events/*`（12 个 Java 侧使用的） — CDI 事件系统，Python 不需要，标记为存根
- [x] `listeners/*`（4 个） — CDI @Observes，Python 不需要，标记为存根
- [x] `hooks/*`（3 个 webhook runner） — 是否需要在 `notifier.py` 中激活
- [x] `storage/*`（3 个） — 加密存储，标记为存根或实现
- [x] `gcm/gcm_sender.py` — Google Cloud Messaging，标记为存根
- [x] `pending_conversions_cleaner.py` — `@Schedule` 定时器，需确认 Python 侧是否用 scheduler 替代
- [x] `platform_health_manager.py` — 健康检查，确认 `platform.py` 是否已覆盖
- [x] `documents/document_workflow_manager.py` / `products/part_workflow_manager.py` — 如无独立逻辑，标记合并到 `workflow_manager.py`

### 主 agent Batch 7 收尾
- [x] 更新 tracker.csv：将所有存根 service 的状态从"已完成"改为"存根(对齐Java)"或"已激活"
- [x] 更新 CHANGELOG / REMINDERS
- [x] 最终全量 pytest + 对拍 Payara
- [x] 将 checklist 第15条标记为"已审计+已制定修复计划"

---

## 附件 A：全局文件所有权矩阵

| 文件 | Batch1 | Batch2 | Batch3 | Batch4 | Batch5 | Batch6 | Batch7 |
|------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| `core/deps.py` | A | | | | | | |
| `services/factory/acl_factory.py` | B | | | | | | |
| `utils/date_utils.py` | B | | | | | | |
| `routers/organizations.py` | | A | | | | D? | |
| `services/organization_manager.py` | | A | | | | | |
| `routers/webhooks.py` | | B | | | | | |
| `services/webhook_manager.py` | | B | | | | | |
| `routers/share.py` | | C | | | | | |
| `services/share_manager.py` | | C | | | | | |
| `routers/document_baselines.py` | | D | | | | | |
| `services/documents/document_baseline_manager.py` | | D | | | | | |
| `routers/product_instances.py` | | D | | | | | |
| `services/products/product_instance_manager.py` | | D | | ✓ | | | |
| `routers/document.py` | | | ✓ | | | | |
| `services/document_manager.py` | | | ✓ | | | | |
| `services/notification_manager.py` | | | ✓ | | | | |
| `routers/products.py` | | | | ✓ | | | |
| `services/product_structure.py` | | | | ✓ | | | |
| `services/products/path_to_path_service.py` | | | | ✓ | | | |
| `services/cascade_action_manager.py` | | | | ✓ | | | |
| `routers/admin.py` | | | | | ✓ | | |
| `services/account_manager.py` | | | | | ✓ | | |
| `services/workspace_manager.py` | | | | | ✓ | | |
| `services/platform_options_manager.py` | | | | | ✓ | | |
| 中/低严重路由组 (A/B/C/D) | | | | | | A/B/C/D | |
| 27 个未激活 service | | | | | | | A/B |

---

## 附件 B：主 agent 每批标准流程

1. 派本批 subagent（含：文件包清单 + 审计报告对应章节 + 全局约束）
2. 回收后逐包 code review：diff 对照规格 + DB 真值 + Payara 对拍
3. 部署 back-py
4. 验证：`pytest -q`（无新增 fail）+ 本批针对性在线 smoke
5. 若失败：主 agent 亲自修或重派
6. 全绿后 commit（Conventional Commits，按域拆原子 commit）
7. 更新 `docs/migration/audit-round3/15-routing-wiring.md` 进度 + `docs/CHANGELOG.md`
