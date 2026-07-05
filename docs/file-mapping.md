# Java → Python 文件映射表

> AI 逐文件 5 维度检查（方法覆盖 / SQL 逻辑 / 异常对齐 / 响应字段 / Stub 检测）。  
> 首次审计 60 对 → 35 问题 → 全修。最后审计日期：2026-07-05。

## 映射对

| # | 域 | Java（ejb / rest） | Python（service / router） |
|---|-----|-------------------|--------------------------|
| 1 | 零件 CRUD | ProductManagerBean | product_service |
| 2 | | PartsResource, PartResource | parts |
| 3 | | 文件上传下载 | PartBinaryResource | part_files |
| 4 | | DTO 映射 | — | part_mapper |
| 5 | | 零件模板 | PartTemplateResource, PartTemplateBinaryResource | parts |
| 6 | | 有效性 | EffectivityResource, PartEffectivityResource | parts（stub） |
| 7 | | 导入 | ImporterBean | parts（stub） |
| 8 | CAD 转换 | ConverterBean | conversion_service |
| 9 | | Kafka 生产者 | — | kafka_producer |
| 10 | 文档 CRUD | DocumentManagerBean | document_service |
| 11 | | DocumentsResource, DocumentResource | documents |
| 12 | | 文件上传下载 | DocumentBinaryResource | document_files |
| 13 | | 文件夹 | FolderResource | folders |
| 14 | | 文档模板 | DocumentTemplateResource, DocumentTemplateBinaryResource | document_templates |
| 15 | | 文档基线 | DocumentBaselinesResource | documents |
| 16 | 产品结构 | ProductManagerBean（CI 部分）, PSFilterManagerBean | product_structure_service |
| 17 | | ProductResource | products |
| 18 | | 产品基线 | ProductBaselinesResource | products |
| 19 | | 产品配置 | ProductConfigurationsResource | products |
| 20 | | 产品实例 | ProductInstancesResource, ProductInstanceBinaryResource | product_instances, product_files |
| 21 | | 图层/Marker | LayerResource | products |
| 22 | 变更管理 | ChangeManagerBean | change_service |
| 23 | | ChangeIssuesResource, ChangeRequestsResource, ChangeOrdersResource, MilestonesResource | changes |
| 24 | 工作流 | WorkflowManagerBean, TaskManagerBean | workflow_service |
| 25 | | WorkflowModelResource, WorkflowResource, WorkspaceWorkflowResource, TaskResource | workflows |
| 26 | 用户/组 | UserManagerBean | user_mgmt_service |
| 27 | | UserResource, UserGroupResource, WorkspaceMembershipResource | users |
| 28 | 账号 | AccountManagerBean | user_mgmt_service |
| 29 | | AccountResource, AuthResource | accounts, auth |
| 30 | 角色/权限 | — | security_service, acl_helper |
| 31 | | RoleResource | roles |
| 32 | 通知 | NotificationManagerBean | notification_service |
| 33 | | ModificationNotificationResource | notifications |
| 34 | Webhook | WebhookManagerBean | — |
| 35 | | WebhookResource | webhooks |
| 36 | 工作区 | WorkspaceManagerBean | — |
| 37 | | WorkspaceResource | workspaces |
| 38 | 管理员 | AdminResource, PlatformResource | admin, misc |
| 39 | 组织 | OrganizationManagerBean, OrganizationResource | organizations |
| 40 | 共享 | ShareManagerBean, SharedResource | shared |
| 41 | LOV / 标签 / 属性 | LOVManagerBean, LOVResource, TagResource, AttributesResource | workspaces |
| 42 | 文件存储 | BinaryStorageManagerBean | file_service, vault |

> 注：后缀 `ManagerBean` / `Resource` 为 Java 框架约定，Python 默认 `_service` / `.py`。

## 检查 Prompt 模板

```markdown
Audit Java→Python migration for: {DOMAIN_NAME}

Java root: /home/chenweibo/CATIA-Copilot-PLM/docdoku-plm-server/
Python root: /home/chenweibo/CATIA-Copilot-PLM/docdoku-plm-server-py/app/

Check 5 dimensions:
1. Method coverage — Java public methods → Python equivalent?
2. SQL logic — same tables/JOINs/WHERE? 🚨 Java = ground truth
3. Exception alignment — Java throw → Python raise with same i18n key?
4. Response fields — Java DTO fields → Python dict keys?
5. Stub detection — hardcoded []/{}/{"status":"ok"} without db.commit()?

Output: METHOD | STATUS (✅/❌/⚠) | DETAIL
```

## 使用方式

```bash
# 全量审计
python3 scripts/file_pair_audit.py --all

# 单域
python3 scripts/file_pair_audit.py --domain parts     # 对 1-7
python3 scripts/file_pair_audit.py --domain documents # 对 10-15
python3 scripts/file_pair_audit.py --domain products  # 对 16-21
python3 scripts/file_pair_audit.py --domain changes   # 对 22-23
```

## 审计历史

| 日期 | 发现 | 修复 | 剩余 |
|------|------|------|------|
| 2026-07-05 | 35（15 Critical + 20 Partial） | 全修（10 批并行 agent） | 0 |
| 2026-07-05（复查） | 11 Partial | 全修（7 批并行 agent） | 0 |
