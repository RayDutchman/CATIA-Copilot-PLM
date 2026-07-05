# 建议的新文件映射 — 待确认（已按 Java 源码修正）

> Router 22→32（对齐 Java Resource），Service 重命名（对齐 Java Bean 名称）  
> 修正：Effectivity 合并1文件 / Workflow 合并1文件 / Shared→share.py

| # | Java Bean | Java REST Resource | Python Service | Python Router | 功能域 |
|---|-----------|-------------------|----------------|---------------|--------|
| 1 | `ProductManagerBean.java` | — | `product_manager.py` | — | 零件 CRUD + 签出签入 |
| 2 | — | — | `part_mapper.py` | — | DTO 映射 |
| 3 | — | `PartsResource.java` | — | `parts.py` | 零件列表/搜索/统计/模板/导入 |
| 4 | — | `PartResource.java` | — | `part.py` | 单个零件 CRUD |
| 5 | — | `PartTemplateResource.java` | — | `part_templates.py` | 零件模板 |
| 6 | — | `PartBinaryResource.java` | — | `part_files.py` | 文件上传下载 |
| 7 | — | `EffectivityResource.java`, `PartEffectivityResource.java` | — | `effectivity.py` | 有效性（合1文件） |
| 8 | `ConverterBean.java` | — | `converter.py` | — | CAD 转换 |
| 9 | `DocumentManagerBean.java` | — | `document_manager.py` | — | 文档 CRUD |
| 10 | — | `DocumentsResource.java` | — | `documents.py` | 文档列表/搜索 |
| 11 | — | `DocumentResource.java` | — | `document.py` | 单个文档 CRUD |
| 12 | — | `DocumentBaselinesResource.java` | — | `document_baselines.py` | 文档基线 |
| 13 | — | `FolderResource.java` | — | `folders.py` | 文件夹 CRUD |
| 14 | — | `DocumentTemplateResource.java` | — | `document_templates.py` | 文档模板 |
| 15 | — | `DocumentBinaryResource.java` | — | `document_files.py` | 文件上传下载 |
| 16 | `ProductManagerBean.java` (CI) | — | `product_structure.py` | — | 产品结构树 |
| 17 | — | `ProductResource.java` | — | `products.py` | 产品/CI REST |
| 18 | — | `ProductBaselinesResource.java` | — | `product_baselines.py` | 产品基线 |
| 19 | — | `ProductConfigurationsResource.java` | — | `product_configurations.py` | 产品配置 |
| 20 | — | `ProductInstancesResource.java`, `ProductInstanceBinaryResource.java` | — | `product_instances.py`, `product_files.py` | 产品实例 + 文件 |
| 21 | — | `LayerResource.java` | — | `layers.py` | 图层/Marker |
| 22 | `ChangeManagerBean.java` | — | `change_manager.py` | — | 变更 CRUD |
| 23 | — | `ChangeIssuesResource.java` | — | `change_issues.py` | Issue 端点 |
| 24 | — | `ChangeRequestsResource.java` | — | `change_requests.py` | Request 端点 |
| 25 | — | `ChangeOrdersResource.java` | — | `change_orders.py` | Order 端点 |
| 26 | — | `MilestonesResource.java` | — | `milestones.py` | 里程碑端点 |
| 27 | `WorkflowManagerBean.java`, `TaskManagerBean.java` | — | `workflow_manager.py` | — | 工作流业务 |
| 28 | — | `WorkflowModelResource.java` | — | `workflow_models.py` | 工作流模板 REST |
| 29 | — | `WorkflowResource.java`, `WorkspaceWorkflowResource.java` | — | `workflow.py` | 工作流实例 + 模板（合1文件） |
| 30 | — | `TaskResource.java` | — | `tasks.py` | 任务 REST |
| 31 | `UserManagerBean.java`, `AccountManagerBean.java` | — | `user_manager.py` | — | 用户/账号管理 |
| 32 | — | `UserResource.java` | — | `users.py` | 用户 REST |
| 33 | — | `UserGroupResource.java` | — | `user_groups.py` | 用户组 REST |
| 34 | — | `WorkspaceMembershipResource.java` | — | `workspace_memberships.py` | 成员资格 REST |
| 35 | — | `AccountResource.java`, `AuthResource.java` | — | `accounts.py`, `auth.py` | 账号 + 认证 |
| 36 | — | `RoleResource.java` | — | `roles.py` | 角色 REST |
| 37 | `NotificationManagerBean.java` | — | `notification_manager.py` | — | 通知业务 |
| 38 | — | `ModificationNotificationResource.java` | — | `notifications.py` | 通知 REST |
| 39 | `WebhookManagerBean.java` | — | — | — | Webhook 业务 |
| 40 | — | `WebhookResource.java` | — | `webhooks.py` | Webhook REST |
| 41 | `WorkspaceManagerBean.java` | — | — | — | 工作区管理 |
| 42 | — | `WorkspaceResource.java` | — | `workspaces.py` | 工作区 REST + stats |
| 43 | — | `TagResource.java`, `LOVResource.java`, `AttributesResource.java` | — | `workspaces.py` | 标签/LOV/属性 |
| 44 | `BinaryStorageManagerBean.java` | — | `binary_storage.py`, `vault.py` | — | 文件存储 |
| 45 | `ShareManagerBean.java` | — | — | `share.py` | 共享 |
| 46 | — | `SharedResource.java` | — | `share.py` | 共享端点 |
| 47 | — | `AdminResource.java` | — | `admin.py` | 管理员面板 |
| 48 | — | `OrganizationResource.java` | — | `organizations.py` | 组织管理 |
| 49 | — | `PlatformResource.java` | — | `platform.py` | 平台/health |
| 50 | — | `LanguagesResource.java` | — | `languages.py` | 语言列表 |
| 51 | — | `TimeZoneResource.java` | — | `timezones.py` | 时区列表 |
| 52 | `ImporterBean.java` | — | — | `parts.py` | 属性/BOM 导入 |

## 变更清单

**Router 拆分** (22→32，+10 文件)：

| 原文件 | 拆出 |
|--------|------|
| `parts.py` | `part.py` + `part_templates.py` + `effectivity.py` |
| `documents.py` | `document.py` + `document_baselines.py` |
| `changes.py` | `change_issues.py` + `change_requests.py` + `change_orders.py` + `milestones.py` |
| `products.py` | `product_baselines.py` + `product_configurations.py` + `layers.py` |
| `users.py` | `user_groups.py` + `workspace_memberships.py` |
| `workflows.py` | `workflow_models.py` + `tasks.py` + `workflow.py` |
| `misc.py` | `languages.py` + `timezones.py` + `platform.py` |
| `shared.py` | → `share.py`（改名） |

**Service 改名** (10 个)：

| 原文件名 | 新文件名 |
|----------|----------|
| `product_service.py` | `product_manager.py` |
| `document_service.py` | `document_manager.py` |
| `change_service.py` | `change_manager.py` |
| `workflow_service.py` | `workflow_manager.py` |
| `user_mgmt_service.py` | `user_manager.py` |
| `conversion_service.py` | `converter.py` |
| `notification_service.py` | `notification_manager.py` |
| `product_structure_service.py` | `product_structure.py` |
| `file_service.py` | `binary_storage.py` |
| — | `security_service.py` / `acl_helper.py` / `kafka_producer.py` / `part_mapper.py` / `vault.py` 不变 |

## 实施计划

按依赖顺序分 3 步：

### Step 1: Service 改名（低风险——只改文件名 + import）
- `git mv` 10 个 service 文件
- 更新 `main.py` 中的 import
- 更新所有 router 文件中的 import
- 更新所有 test 文件中的 import
- 更新其他 service 文件之间的相互 import
- 跑测试确认

### Step 2: Router 拆分（中风险——内容移动 + 新文件）
- 从 7 个大文件拆出 17 个新文件（合并原 +10）
- 每个新文件：移动对应端点代码 + 独立 `router = APIRouter(prefix=...)`
- 更新 `main.py` 注册所有新 router
- 保留原文件中的剩余端点（缩小后的文件）
- 跑测试确认

### Step 3: 文档更新
- `file-mapping.md` 替换为最终映射
- `file-mapping-proposed.md` 删除

确认后按 1→2→3 执行？
