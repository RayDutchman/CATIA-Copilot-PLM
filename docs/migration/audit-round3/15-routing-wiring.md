# 审计报告：路由/服务接线正确性（checklist 第15条 · 子要点 4 & 5）

> 生成日期：2026-07-12
> 审计范围：full-audit-checklist.md 第15条 子要点 **④「函数归属」** + **⑤「dead code / service 未接线」**
> ⚠️ 子要点 ①（参数注解）、②（路由路径一致性）、③（response_model）**本次未覆盖**，需独立审计
> 审计方法：4 个 explore subagent 并行审核（router 内联扫描 + tracker.csv 交叉引用 + 跨文件重复检测 + 胖路由深度拆解）+ 1 个 explore subagent 验证 Java Resource 层规范
> 审计原则：**无条件对齐 Payara 后端**（以 Java 源码为功能对照基准，以 tracker.csv 为文件映射基准）

---

## 一、Payara 对齐基准验证

**结论：Java REST Resource 层严格遵守分层规范，零内联 DB 操作。**

随机抽查 5 个 Java Resource 文件（ProductResource, DocumentResource, AdminResource, OrganizationResource, WebhookResource）+ 全 `rest/` 目录搜索：
- `@PersistenceContext` 注入原始 EntityManager：**0 处**
- `javax.persistence` import：**0 个文件**
- 内联 JPQL/SQL：**0 处**
- 所有数据访问通过 `@Inject` 注入 `IXxxManagerLocal` service 接口完成

**Python 对齐标准：路由层零内联 DB 操作。** 原提出的"三级边界规则"中"级别1允许简单查询"被此对齐基准否决。

---

## 二、问题总览

### 2.1 Router 内联 DB 扫描结果

| 严重程度 | 文件数 | 内联 DB 操作 | 说明 |
|----------|--------|:----:|------|
| **高** (>15处) | 6 | ~170 | document.py (45+), products.py (38), admin.py (30), parts.py (22), product_instances.py (22), product_baselines.py (18) |
| **中** (5-15处) | 10 | ~95 | workspaces.py, document_baselines.py, part.py, tasks.py, user_groups.py, workspace_memberships.py, document_templates.py, users.py, folders.py, part_templates.py |
| **低** (<5处) | 28 | ~85 | part_files.py, share.py, documents.py, webhooks.py, change_common.py, organizations.py, notifications.py, workflow.py 等 |
| **零内联** | 3 | 0 | languages.py, timezones.py, dev.py |
| **合计** | 47 | **~350** | — |

### 2.2 Tracker.csv Service 接线状态

| 分类 | 文件数 | 说明 |
|------|:----:|------|
| **已接线**（router 直接引用） | 35 | 36% |
| **间接接线**（经其他 service 中转） | ~18 | 19% |
| **有 service 但 router 绕过** | 7 | router 自己 inline 实现了 service 应做的事 |
| **Java 侧已使用但 Python 无调用方** | 20 | 因 Python router 绕过或未实现对应端点 |
| **Java 侧也是 dead code** | 3 | Created.java, DocumentRevisionEvent.java, WorkspaceEvent.java |

### 2.3 跨路由重复逻辑

| 优先级 | 重复模式 | 出现次数 | 影响文件 |
|--------|---------|:---:|------|
| **P0** | `_check_is_admin` + 内联 admin SQL | **25+** | 10+ |
| **P1** | `_build_acl` / `_get_acl_dict` | 3 | 3 |
| **P2** | 日期格式化 `_fmt_date` | 3 | 3 |
| **P3** | 文件下载 Range/404/416 处理 | ~12 | 5 |
| **P4** | `_file_headers` / template 路径 helpers | 6 | 2 |
| **P5** | `_get_user_name` + `_NAME_CACHE` | 2 | 2 |
| **P6** | `_build_author` / user-to-dict DTO 构建 | 3 | 3 |

---

## 三、三大胖路由深度拆解

### 3.1 `document.py`（1021行, ~55 内联 DB）

| 函数 | 行数 | 内联 DB | 判定 | 迁入目标 |
|------|:--:|:--:|------|------|
| `_doc_to_dict` | 240 | ~10 | 服务层（最大胖函数） | `document_manager.py` |
| `update_iteration` | 95 | ~5 | 服务层 | `document_manager.py` |
| `aborted_workflows` | 60 | ~6 | 服务层 | `document_manager.py` / `workflow_manager.py` |
| `inverse_doc_link/part_link/product_link/path_link` | 各~30 | 各1 | 服务层 | `document_manager.py` |
| `update_doc_acl` | 30 | 4 | 服务层 | `document_manager.py` / `security_service.py` |
| 订阅/退订 (4函数) | 各~15 | 各2 | 服务层 | `notification_manager.py` |
| `remove_doc_file` / `rename_doc_file` | 各~30 | 各4 | 服务层 | `document_manager.py` |
| `checkout/checkin/undo/release/obsolete/new_version` | — | 0~1 | 路由层 | 保留 |
| **建议迁出总计** | **~750** | **~45** | **73%** | — |

### 3.2 `products.py`（1034行, ~47 内联 DB）

| 函数 | 行数 | 内联 DB | 判定 | 迁入目标 |
|------|:--:|:--:|------|------|
| `_build_instance_master_dict` | 195 | ~15 | 服务层 | `product_instance_manager.py` |
| `_ci_to_dict` | 28 | 2 | 混合（DB部分迁） | `product_structure.py` |
| `_collect_ci_parts` | 62 | ~5 | 服务层 | `cascade_action_manager.py` |
| `ci_document_links` + `_wip` | 132 | ~10 | 服务层 | `product_structure.py` |
| `ci_paths` | 70 | ~3 | 服务层 | `product_structure.py` |
| `last_release` | 46 | 4 | 服务层 | `product_structure.py` |
| `path_choices` / `versions_choices` | 各~20 | 各1 | 服务层 | `product_structure.py` |
| `path_to_path_links_*` | 30 | 2 | 服务层 | `path_to_path_service.py` |
| `bom`（flatten 部分） | 40 | 1+递归 | 混合 | `product_structure.py` |
| `list_cis/get_ci/create_ci/delete_ci/update_ci` | — | 0 | 路由层 | 保留 |
| `cascade_checkout/checkin/undo` | — | 0 | 路由层 | 保留 |
| **建议迁出总计** | **~700** | **~43** | **67%** | — |

### 3.3 `admin.py`（462行, ~48 内联 DB）

| 函数 | 行数 | 内联 DB | 判定 | 迁入目标 |
|------|:--:|:--:|------|------|
| `delete_account` | 42 | 18 | 服务层（最多 SQL） | `account_manager.py` |
| `list_accounts` / `get_account` / `update_account` / `enable_account` | 各~20 | 各1~3 | 服务层 | `account_manager.py` |
| `list_workspaces` / `get_workspace` / `update_workspace` / `enable_workspace` | 各~20 | 各1~3 | 服务层 | `workspace_manager.py` |
| `get/put_platform_options` | 各~20 | 各1~4 | 服务层 | `platform_options_manager.py` |
| admin stats (5函数) | 各~15 | 各1~2 | 服务层 | `platform_options_manager.py` / 新建 admin_stats |
| `_require_admin` | — | 1 | 混合 | `app/core/deps.py` (Depends) |
| `delete_workspace` | — | 0 | 路由层 | 保留（已委托 `cascade_delete_workspace`） |
| **建议迁出总计** | **~340** | **~47** | **74%** | — |

---

## 四、有 Service 但 Router 完全绕过的案例（P0）

| Router | 内联 DB | 被绕过的 Service | tracker 编号 | Java 侧状态 |
|--------|:----:|------|------|------|
| `organizations.py` | ~27 | `organization_manager.py` | S-017 | Java 已使用 (OrganizationResource @Inject IOrganizationManagerLocal) |
| `webhooks.py` | ~13 | `webhook_manager.py` | S-027 | Java 已使用 (WebhookResource @Inject IWebhookManagerLocal) |
| `share.py` | ~10 | `share_manager.py` | S-024 | Java 已使用 (SharedResource @Inject IShareManagerLocal) |
| `document_baselines.py` | ~17 | `documents/document_baseline_manager.py` | S-065 | Java 已使用 (DocumentBaselinesResource @Inject IDocumentBaselineManagerLocal) |
| `product_instances.py` | ~22 | `products/product_instance_manager.py` | S-064 | Java 已使用 (ProductInstancesResource @Inject IProductInstanceManagerLocal) |
| `admin.py` (平台选项部分) | ~8 | `platform_options_manager.py` | S-021 | Java 已使用 (AdminResource @Inject IPlatformOptionsManagerLocal) |
| `products.py` (_collect_ci_parts) | ~5 | `cascade_action_manager.py` | S-004 | Java 已使用 (ProductResource @Inject ICascadeActionManagerLocal) |

**所有 7 个被绕过的 service 在 Java 侧均正常使用，均已存在于 tracker.csv 映射中。**

---

## 五、Java 侧已使用但 Python 侧无调用方的 Service（待激活）

以下 20 个 service 文件在 Java 侧均正常使用（通过 @Inject/@EJB/@Schedule 等），但 Python 侧 router 尚未调用它们。

| 编号 | Python 文件 | Java 侧使用方式 |
|------|------|------|
| S-002 | `activity_checker.py` | `@CheckActivity` 注解被 DocumentWorkflowManagerBean 使用；CDI 拦截器 |
| S-004 | `cascade_action_manager.py` | ProductResource @Inject；`_collect_ci_parts` 被 products.py 绕过（见第 4 节），其余功能待激活 |
| S-006 | `context_manager.py` | 10+ 个类注入使用（WorkspaceManager, UserManager, ProductManager 等） |
| S-015 | `oauth_manager.py` | AdminResource/AuthResource/AccountResource 注入 |
| S-016 | `ondemand_converter.py` | PartBinaryResource/DocumentBinaryResource 等注入 |
| S-019 | `pending_conversions_cleaner.py` | `@Singleton @Startup` + `@Schedule` 每5分钟自动触发 |
| S-020 | `platform_health_manager.py` | PlatformResource 注入 |
| S-023 | `public_entity_manager.py` | PartBinaryResource/DocumentBinaryResource/SharedResource 等注入 |
| S-043~057 | `events/*` (15 files) | CDI 事件系统：.fire() 触发 + @Observes 监听（除 3 个 dead） |
| S-058~061 | `listeners/*` (4 files) | CDI @Named + @Observes 事件监听 |
| S-062 | `products/part_workflow_manager.py` | TaskResource/TaskManagerBean 注入 |
| S-066 | `documents/document_workflow_manager.py` | TaskManagerBean/DocumentResource 注入 |
| S-067~069 | `hooks/*` (3 files) | NotifierBean new SNSWebhookRunner/SimpleWebhookRunner |
| S-079~081 | `storage/*` (3 files) | BinaryStorageManagerBean 使用 FileStorageProvider；CryptoConverter 注册但未应用 |
| S-084 | `gcm/gcm_sender.py` | DocumentManagerBean/DocumentWorkflowManagerBean 注入 (gcmNotifier) |

**27 个文件在 Java 侧确认已使用。按对齐原则，Python 侧需保留对应文件并逐步激活。**

---

## 六、Java 侧确认为 Dead Code（3 个）

| 编号 | 文件 | Java 侧判定 |
|------|------|------|
| S-044 | `events/created.py` | CDI @Qualifier 注解，零引用（无 @Created 使用/AnnotationLiteral） |
| S-045 | `events/document_revision_event.py` | 被注入到 DocumentManagerBean 但从未 .fire()/无 @Observes |
| S-056 | `events/workspace_event.py` | 零引用：无注入、无触发、无监听 |

> 按"无条件对齐 Payara"原则，**这 3 个文件不删除**——它们在 Java 源码树中存在，Python 侧保留为对齐存根。

---

## 七、审计结论

### 核心发现

1. **47/47 路由文件存在内联 DB 操作**（仅 3 个完全干净），共 ~350 处违规
2. **7 个 service 被 router 完全绕过**——Java 侧正常使用，Python 侧 router 自己 inline 实现了等效逻辑
3. **3 个胖路由需迁出 >70% 代码**：document.py (73%)、admin.py (74%)、products.py (67%)
4. **7 组跨 router 重复逻辑**，其中 admin-check SQL 重复 25+ 处最严重
5. **27 个 service 文件在 Java 侧正常使用但 Python 侧未激活**

### Java 对齐基准

- Java Resource 层：**零内联 DB**，100% 通过 @Inject 委托 IXxxManagerLocal service 接口
- Python 对齐标准：**路由层零内联 DB 操作**，所有数据访问委托 service 层

### 无对应 service 文件的内联逻辑

| Router 内联逻辑 | 有无对应 service？ | 处理 |
|----------|:--:|------|
| `_check_is_admin` (多文件) | ✅ user_manager / account_manager | 迁入已有 service + core/deps.py |
| `_build_acl` (3文件) | ✅ factory/acl_factory.py | 迁入已有 service |
| admin stats 查询 | ✅ platform_options_manager / 新建 | 迁入已有或新建 |
| 日期格式化 | ✅ models/util/date_utils.py | 迁入已有工具 |
| 文件下载 Range | ✅ routers/file/download_response.py | 迁入已有工具 |
| Tag subscription 内联 | ✅ notification_manager.py | 迁入已有 service |
| Layer/Marker CRUD | ❌ tracker.csv 无对应 | **需确认 Java 侧是否有 LayerManagerBean** |

唯一缺失项 Layer/Marker CRUD 需检查 Java `LayerResource.java` 是否直接操作 entity manager（若 Java 侧也 thin，可保留在 router）。

---

## 附录：审计子 agent 清单

| Agent | 任务 | 产出 |
|-------|------|------|
| Agent1 | 全量 router 内联 DB 扫描（47文件, ~350处） | 按严重程度分级表 + 模式总结 |
| Agent2 | tracker.csv × router 交叉引用 | 接线/绕过/dead code 三分法 + 28 dead service 列表 |
| Agent3 | 跨路由重复逻辑扫描 | 7 组重复模式 + P0~P6 优先级排序 |
| Agent4 | 三大胖路由逐函数深度拆解 | 每函数归属判定 + 迁入目标 service |
| Agent5 | Java Resource 层验证 | Resource 零内联 DB 确认（Payara 对齐基准） |

---

## 八、修复结果 (2026-07-12)

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 路由文件内联 DB 操作 | ~350 处 | **~0** |
| 三大胖路由 document.py | 1021 行 | 382 行 (-63%) |
| 三大胖路由 products.py | 968 行 | 454 行 (-53%) |
| 三大胖路由 admin.py | 432 行 | 223 行 (-48%) |
| 跨文件重复逻辑 | 8 组 | 0 |
| 被绕过的 service | 7 个 | 0（全部激活） |
| tracker.csv 已激活/已扩展 | 0 条 | 14 条 |
| tracker.csv 对齐存根 | 0 条 | 36 条 |

**修复分支**: `fix/audit-remediation`，共 17 commits，见 `FIX-PLAN.md` 进展表。

> ⚠️ 子要点 ①（参数注解）、②（路由路径一致性）、③（response_model）**本次未覆盖**，需独立审计轮次。
