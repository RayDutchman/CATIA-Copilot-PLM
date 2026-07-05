# Java → Python 文件映射表

> 用于 AI 逐文件对比检查：方法覆盖 / SQL 查询逻辑 / 异常对齐 / 响应字段 / Stub 检测。

## 映射对

| # | Java Bean | Java REST Resource | Python Service | Python Router | 功能域 |
|---|-----------|-------------------|----------------|---------------|--------|
| 1 | `ProductManagerBean.java` | — | `product_service.py` | — | 零件 CRUD + 签出签入 + BOM |
| 2 | `ProductManagerBean.java` | — | `part_mapper.py` | — | 零件 DTO 映射 |
| 3 | — | `PartsResource.java` | — | `parts.py` | 零件列表/搜索/统计 |
| 4 | — | `PartResource.java` | — | `parts.py` | 单个零件 CRUD/tags |
| 5 | — | `PartBinaryResource.java` | — | `part_files.py` | 零件文件上传下载 |
| 6 | `ConverterBean.java` | — | `conversion_service.py` | — | CAD 转换回调 |
| 7 | `DocumentManagerBean.java` | — | `document_service.py` | — | 文档 CRUD + 签出签入 |
| 8 | — | `DocumentsResource.java` | — | `documents.py` | 文档列表/搜索/统计 |
| 9 | — | `DocumentResource.java` | — | `documents.py` | 单个文档 CRUD/tags |
| 10 | — | `FolderResource.java` | — | `folders.py` | 文件夹 CRUD |
| 11 | — | `DocumentTemplateResource.java` | — | `document_templates.py` | 文档模板 |
| 12 | — | `DocumentBinaryResource.java` | — | `document_files.py` | 文档文件上传下载 |
| 13 | — | `DocumentBaselinesResource.java` | — | `documents.py` | 文档基线 |
| 14 | `ProductManagerBean.java` (CI) | — | `product_structure_service.py` | — | 产品 CI + 结构树 + 基线 |
| 15 | — | `ProductResource.java` | — | `products.py` | 产品/CI REST |
| 16 | — | `ProductBaselinesResource.java` | — | `products.py` | 产品基线 |
| 17 | — | `ProductConfigurationsResource.java` | — | `products.py` | 产品配置 |
| 18 | — | `ProductInstancesResource.java` | — | `product_instances.py` | 产品实例 |
| 19 | — | `ProductInstanceBinaryResource.java` | — | `product_files.py` | 产品实例文件 |
| 20 | `ChangeManagerBean.java` | — | `change_service.py` | — | 变更 CRUD |
| 21 | — | `ChangeIssuesResource.java` | — | `changes.py` | Issue 端点 |
| 22 | — | `ChangeRequestsResource.java` | — | `changes.py` | Request 端点 |
| 23 | — | `ChangeOrdersResource.java` | — | `changes.py` | Order 端点 |
| 24 | — | `MilestonesResource.java` | — | `changes.py` | 里程碑端点 |
| 25 | `WorkflowManagerBean.java` | — | `workflow_service.py` | — | 工作流业务 |
| 26 | `TaskManagerBean.java` | — | `workflow_service.py` | — | 任务审批业务 |
| 27 | — | `WorkflowModelResource.java` | — | `workflows.py` | 工作流模板 REST |
| 28 | — | `TaskResource.java` | — | `workflows.py` | 任务 REST |
| 29 | `UserManagerBean.java` | — | `user_mgmt_service.py` | — | 用户/组管理业务 |
| 30 | `AccountManagerBean.java` | — | `user_mgmt_service.py` | — | 账号管理业务 |
| 31 | — | `UserResource.java` | — | `users.py` | 用户 REST |
| 32 | — | `UserGroupResource.java` | — | `users.py` | 用户组 REST |
| 33 | — | `WorkspaceMembershipResource.java` | — | `users.py` | 成员资格 REST |
| 34 | — | `AccountResource.java` | — | `accounts.py` | 账号 REST |
| 35 | — | `AuthResource.java` | — | `auth.py` | 认证端点 |
| 36 | — | `RoleResource.java` | — | `roles.py` | 角色 REST |
| 37 | `NotificationManagerBean.java` | — | `notification_service.py` | — | 通知业务 |
| 38 | — | `ModificationNotificationResource.java` | — | `notifications.py` | 通知 REST |
| 39 | `WebhookManagerBean.java` | — | — | — | Webhook 业务 |
| 40 | — | `WebhookResource.java` | — | `webhooks.py` | Webhook REST |
| 41 | `WorkspaceManagerBean.java` | — | — | `workspaces.py` | 工作区管理业务 |
| 42 | — | `WorkspaceResource.java` | — | `workspaces.py` | 工作区 REST（stats/front-options等） |
| 43 | `BinaryStorageManagerBean.java` | — | `file_service.py` + `vault.py` | — | 文件存储 |
| 44 | `ShareManagerBean.java` | — | — | `shared.py` | 共享 |
| 45 | — | `AdminResource.java` | — | `admin.py` | 管理员面板 |
| 46 | — | `OrganizationResource.java` | — | `organizations.py` | 组织管理 |
| 47 | — | `PlatformResource.java` | — | `misc.py` | 平台/语言/时区 |
| 48 | `LOVManagerBean.java` | `LOVResource.java` | — | `workspaces.py` | 值列表 |
| 49 | — | `TagResource.java` | — | `workspaces.py` | 标签管理 |
| 50 | — | `AttributesResource.java` | — | `workspaces.py` | 属性管理 |
| 51 | `EffectivityManagerBean.java` | `EffectivityResource.java` | — | — | 有效性管理（**缺 Python 实现**） |
| 52 | — | `PartEffectivityResource.java` | — | — | 零件有效性（**缺 Python 实现**） |
| 53 | — | `PartTemplateResource.java` | — | `parts.py`（部分） | 零件模板 CRUD |
| 54 | — | `PartTemplateBinaryResource.java` | — | `parts.py`（部分） | 零件模板文件 |
| 55 | — | `LayerResource.java` | — | — | 产品图层/Marker（**缺 Python 实现**） |
| 56 | `ImporterBean.java` | — | — | `parts.py`（import 端点） | 属性/BOM 导入 |
| 57 | `OrganizationManagerBean.java` | `OrganizationResource.java` | — | `organizations.py` | 组织管理 |
| 58 | `PlatformOptionsManagerBean.java` | `PlatformResource.java` | — | `admin.py` | 平台选项 |
| 59 | `PlatformHealthManagerBean.java` | — | — | `misc.py` | 平台健康检查 |
| 60 | `PublicEntityManagerBean.java` | — | — | — | 公开实体管理（无直接 REST 端点） |

## 检查 Prompt 模板

```markdown
You are auditing a Java→Python migration file pair.

Java file: {JAVA_FILE_PATH}
Python file: {PYTHON_FILE_PATH}

Check these 5 dimensions:

1. **方法覆盖率** — List all public methods in Java. Which ones have a Python equivalent? Mark ❌ for missing.
2. **SQL查询逻辑** — For each method that queries DB: does Python use the same tables, same JOINs, same WHERE conditions? If not, spell out the diff.
3. **异常对齐** — For each Java throw: does Python raise the corresponding ApplicationException with the matching i18n key?
4. **响应字段** — For each Java endpoint returning DTO: does Python return the same field names and nested structure?
5. **Stub检测** — For each Python method returning hardcoded `[]`, `{}`, `{"status":"ok"}`, or `return 204` without `db.commit()`: mark ❌ STUB.

Output: summary table with METHOD | VERDICT (✅/❌/⚠) | DETAIL
```

## 使用方式

```bash
# 全量检查
python3 scripts/file_pair_audit.py --all

# 单域检查
python3 scripts/file_pair_audit.py --domain parts  # 对 #1-5
python3 scripts/file_pair_audit.py --domain documents  # 对 #7-13
```

## 检查历史

| 日期 | 检查范围 | 发现问题 | 状态 |
|------|---------|---------|------|
| — | — | — | 首次检查待执行 |
