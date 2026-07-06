# Java → Python 文件映射表

> 用于 AI 逐文件对比检查：方法覆盖 / SQL 查询逻辑 / 异常对齐 / 响应字段 / Stub 检测。  
> 首次审计 60 对 → 35 问题 → 2 轮修复 → 最后审计：2026-07-05。

## 一、业务映射（Router + Service ↔ Java Resource + Bean）

| # | Java Bean | Java REST Resource | Python Service | Python Router | 功能域 | 状态 |
|---|-----------|-------------------|----------------|---------------|--------|------|
| 1 | `ProductManagerBean.java` | — | `product_manager.py` | — | 零件 CRUD + 签出签入 | ✅ |
| 2 | — | — | `part_mapper.py` | — | DTO 映射 | ✅ |
| 3 | — | `PartsResource.java` | — | `parts.py` | 零件列表/搜索/统计/导入 | ✅ |
| 4 | — | `PartResource.java` | — | `part.py` | 单个零件 CRUD | ✅ |
| 5 | — | `PartTemplateResource.java` | — | `part_templates.py` | 零件模板 | ✅ |
| 6 | — | `PartBinaryResource.java` | — | `part_files.py` | 文件上传下载 | ✅ |
| 7 | — | `EffectivityResource.java`, `PartEffectivityResource.java` | — | `effectivity.py` | 有效性 | ⚠️ stub |
| 8 | `ConverterBean.java` | — | `converter.py` | — | CAD 转换 | ✅ |
| 9 | `DocumentManagerBean.java` | — | `document_manager.py` | — | 文档 CRUD | ✅ |
| 10 | — | `DocumentsResource.java` | — | `documents.py` | 文档列表/搜索 | ✅ |
| 11 | — | `DocumentResource.java` | — | `document.py` | 单个文档 CRUD | ✅ |
| 12 | — | `DocumentBaselinesResource.java` | — | `document_baselines.py` | 文档基线 | ✅ |
| 13 | — | `FolderResource.java` | — | `folders.py` | 文件夹 CRUD | ✅ |
| 14 | — | `DocumentTemplateResource.java` | — | `document_templates.py` | 文档模板 | ✅ |
| 15 | — | `DocumentBinaryResource.java` | — | `document_files.py` | 文件上传下载 | ✅ |
| 16 | `ProductManagerBean.java` (CI) | — | `product_structure.py` | — | 产品结构树 | ✅ |
| 17 | — | `ProductResource.java` | — | `products.py` | 产品/CI REST | ✅ |
| 18 | — | `ProductBaselinesResource.java` | — | `product_baselines.py` | 产品基线 | ✅ |
| 19 | — | `ProductConfigurationsResource.java` | — | `product_configurations.py` | 产品配置 | ✅ |
| 20 | — | `ProductInstancesResource.java`, `ProductInstanceBinaryResource.java` | — | `product_instances.py`, `product_files.py` | 产品实例 + 文件 | ✅ |
| 21 | — | `LayerResource.java` | — | `layers.py` | 图层/Marker | ✅ |
| 22 | `ChangeManagerBean.java` | — | `change_manager.py` | — | 变更 CRUD | ✅ |
| 23 | — | `ChangeIssuesResource.java` | — | `change_issues.py` | Issue 端点 | ✅ |
| 24 | — | `ChangeRequestsResource.java` | — | `change_requests.py` | Request 端点 | ✅ |
| 25 | — | `ChangeOrdersResource.java` | — | `change_orders.py` | Order 端点 | ✅ |
| 26 | — | `MilestonesResource.java` | — | `milestones.py` | 里程碑端点 | ✅ |
| 27 | `WorkflowManagerBean.java`, `TaskManagerBean.java` | — | `workflow_manager.py` | — | 工作流业务 | ✅ |
| 28 | — | `WorkflowModelResource.java` | — | `workflow_models.py` | 工作流模板 REST | ✅ |
| 29 | — | `WorkflowResource.java`, `WorkspaceWorkflowResource.java` | — | `workflow.py` | 工作流实例 + 模板 | ✅ |
| 30 | — | `TaskResource.java` | — | `tasks.py` | 任务 REST | ✅ |
| 31 | `UserManagerBean.java`, `AccountManagerBean.java` | — | `user_manager.py` | — | 用户/账号管理 | ✅ |
| 32 | — | `UserResource.java` | — | `users.py` | 用户 REST | ✅ |
| 33 | — | `UserGroupResource.java` | — | `user_groups.py` | 用户组 REST | ✅ |
| 34 | — | `WorkspaceMembershipResource.java` | — | `workspace_memberships.py` | 成员资格 REST | ✅ |
| 35 | — | `AccountResource.java`, `AuthResource.java` | — | `accounts.py`, `auth.py` | 账号 + 认证 | ✅ |
| 36 | — | `RoleResource.java` | — | `roles.py` | 角色 REST | ✅ |
| 37 | `NotificationManagerBean.java` | — | `notification_manager.py` | — | 通知业务 | ✅ |
| 38 | — | `ModificationNotificationResource.java` | — | `notifications.py` | 通知 REST | ✅ |
| 39 | `WebhookManagerBean.java` | — | — | — | Webhook 业务 | ✅ |
| 40 | — | `WebhookResource.java` | — | `webhooks.py` | Webhook REST | ✅ |
| 41 | `WorkspaceManagerBean.java` | — | — | — | 工作区管理 | ✅ |
| 42 | — | `WorkspaceResource.java` | — | `workspaces.py` | 工作区 REST + stats | ✅ |
| 43 | — | `TagResource.java`, `LOVResource.java`, `AttributesResource.java` | — | `workspaces.py` | 标签/LOV/属性 | ✅ |
| 44 | `BinaryStorageManagerBean.java` | — | `binary_storage.py`, `vault.py` | — | 文件存储 | ✅ |
| 45 | `ShareManagerBean.java` | — | — | `share.py` | 共享 | ✅ |
| 46 | — | `SharedResource.java` | — | `share.py` | 共享端点 | ✅ |
| 47 | — | `AdminResource.java` | — | `admin.py` | 管理员面板 | ✅ |
| 48 | — | `OrganizationResource.java` | — | `organizations.py` | 组织管理 | ✅ |
| 49 | — | `PlatformResource.java` | — | `platform.py` | 平台/health | ✅ |
| 50 | — | `LanguagesResource.java` | — | `languages.py` | 语言列表 | ✅ |
| 51 | — | `TimeZoneResource.java` | — | `timezones.py` | 时区列表 | ✅ |
| 52 | `ImporterBean.java` | — | — | `parts.py` | 属性/BOM 导入 | ⚠️ |

> ✅ = 已对齐 | ⚠️ = stub/低频功能

## 二、基础设施映射（无直接 Java 对应文件，但有关联 Java 组件）

| # | Python 文件 | 相关联的 Java 组件 |
|---|-----------|-------------------|
| C1 | `app/core/config.py` | `ConversionServiceConfig.java`，`Back.env` 环境变量 |
| C2 | `app/core/database.py` | `EntityManagerProducer.java` (JPA) |
| C3 | `app/core/deps.py` | `RequestFilter.java` + `JWTokenManager.java` |
| C4 | `app/core/exceptions.py` | `com/docdoku/plm/server/core/exceptions/*.java` (86 文件) |
| C5 | `app/core/exception_handlers.py` | `AccessRightsExceptionMapper.java` 等 |
| C6 | `app/core/i18n.py` | `PropertiesLoader.java` |
| C7 | `app/core/security.py` | `JWTokenManager.java`，`Credential.java` (MD5) |
| C8 | `app/main.py` | `RestApplication.java` (JAX-RS Application) |
| C9 | `app/models/auth.py` | `Account.java`, `Credential.java`, `UserGroupMapping.java` |
| C10 | `app/models/part.py` | `PartMaster.java`, `PartRevision.java`, `PartIteration.java` 等 |
| C11 | `app/models/document.py` | `DocumentMaster.java`, `DocumentRevision.java` 等 |
| C12 | `app/models/product.py` | `ConfigurationItem.java`, `ProductBaseline.java` 等 |
| C13 | `app/models/change.py` | `ChangeIssue.java`, `ChangeRequest.java` 等 |
| C14 | `app/models/workflow.py` | `WorkflowModel.java`, `Workflow.java`, `Activity.java` 等 |
| C15 | `app/models/security.py` | `ACL.java`, `AclUserEntry.java`, `Role.java` |
| C16 | `app/models/user_mgmt.py` | `UserGroup.java`, `Workspace.java` (部分字段) |
| C17 | `app/models/notification.py` | `ModificationNotification.java` |
| C18 | `app/schemas/auth.py` | `AccountDTO.java` |
| C19 | `app/schemas/part.py` | `PartRevisionDTO.java`, `PartIterationDTO.java` 等 (~20 DTO) |
| C20 | `app/services/acl_helper.py` | `ACLFactory.java` (抽象) |
| C21 | `app/services/security_service.py` | `RoleManagerBean.java` (间接) |
| C22 | `app/services/kafka_producer.py` | `ConverterBean.java` (Kafka 部分) |

## 三、文件夹结构

```
app/
├── core/           # 基础设施（config/DB/auth/i18n/异常）— 对应 Java core + i18n 包
├── models/         # ORM 模型 — 对应 Java JPA Entity 类
├── schemas/        # Pydantic 模型 — 对应 Java DTO 类
├── services/       # 业务逻辑 — 对应 Java EJB
└── routers/        # REST 端点 — 对应 Java Resource
```

结构合理：`core(models)→models→services→routers`，依赖方向清晰（router→service→model→core）。无循环依赖，无跨层引用。

## 四、检查 Prompt 模板

```markdown
You are auditing a Java→Python migration file pair.

Java file: {JAVA_FILE_PATH}
Python file: {PYTHON_FILE_PATH}

Check each dimension with comprehensive coverage — don't limit yourself to pre-listed examples:

1. **方法覆盖率** — Read the Java file first. Understand its full public API. Then check Python for logic equivalence, even if names differ. Flag ANY Java method without a Python equivalent.

2. **SQL 查询逻辑** — For EVERY DB operation, compare exact queries: table names, columns, JOINs, WHERE conditions, aggregate functions, GROUP BY, ORDER BY. Java is the ground truth. Flag ANY difference.

3. **异常处理** — For every Java throw/catch, check Python has equivalent i18n key + exception type. Also check: does Python add new error conditions Java doesn't? Does Python silently swallow errors?

4. **响应字段存在性** — Compare EVERY field: name (camelCase), nested structure depth, type (object/array/scalar). Missing or extra fields both count.

5. **Stub 检测** — Any return of `[]`, `{}`, `{"status":"ok"}`, hardcoded booleans, or `Response(status_code=204)` without corresponding DB operations. Don't just pattern-match — verify db.commit() exists for every write path.

6. **值语义正确性** — For each response field, trace the value to its source. What DB table/column? What transformation (type conversion, lookup, mapping, calculation)? Think broadly about ALL value types: nested objects, IDs, timestamps, boolean flags, file paths, URL patterns, enum values, permission codes, etc. If a value looks wrong, it probably is.
```

## 五、审计历史

| 日期 | 发现 | 修复 | 剩余 |
|------|------|------|------|
| 2026-07-05 | 35（15 Critical + 20 Partial） | 全修（10 批并行 agent） | 11 |
| 2026-07-05 | 11 Partial | 全修（7 批并行 agent） | 0 |
| 2026-07-05 | 文件重组：Router 22→32，Service 10 个改名 | — | — |
