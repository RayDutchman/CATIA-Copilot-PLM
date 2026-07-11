# Documents 文档域审计报告

> 审计员：explore subagent ｜ 日期：2026-07-11 ｜ 波次：1
> 范围：document.py / documents.py / document_files.py / document_templates.py / document_template_files.py / folders.py / document_manager.py

## 问题 D-1
- 严重级：CRITICAL
- 类别：要点#9（深拷贝 vs 浅拷贝）
- 位置：`app/services/document_manager.py:366-393`（checkout）
- Java 对照：`DocumentManagerBean.java:905-960`（checkOutDocument，942-956 克隆 linkedDocuments+instanceAttributes）
- 证据：Python checkout 只 `_copy_attached_files`，缺 `_copy_linked_documents` 和 `_copy_instance_attributes`。
- 结论与建议：新迭代丢失 linkedDocuments/instanceAttributes，数据丢失。补两个拷贝调用。

## 问题 D-2
- 严重级：CRITICAL
- 类别：要点#17（端点覆盖缺口）
- 位置：document.py / document_template_files.py 缺 4 端点
- Java 对照：`DocumentResource.java:576-614`、`DocumentTemplateResource.java:256-301`
- 证据：缺 PUT/DELETE 文档迭代内文件（rename/remove）、缺 PUT/DELETE 模板文件（rename/remove）。
- 结论与建议：补 4 端点。

## 问题 D-3
- 严重级：CRITICAL
- 类别：要点#1（业务逻辑完整性）
- 位置：`app/services/document_manager.py:672-715`（update_iteration）+ `app/routers/document.py:483-574`
- Java 对照：`DocumentResource.java:305-345` + `DocumentManagerBean.java:1379-1426`
- 证据：Python 只处理 revisionNote+linkedDocuments，**忽略 instanceAttributes**，且不检查 checkout 用户+末迭代身份（Java 行 1385 检查）。
- 结论与建议：补 instanceAttributes 全量替换；加 checkout 用户/末迭代校验。

## 问题 D-4
- 严重级：CRITICAL
- 类别：要点#17 + #3
- 位置：`app/routers/documents.py:200-208`（create）
- Java 对照：`FolderResource.java:112-151`（createDocumentMasterInFolder）
- 证据：Python 仅取 reference+title，忽略 description/templateId/workflowModelId/acl/roleMapping。
- 结论与建议：补全字段透传。

## 问题 D-5
- 严重级：HIGH
- 类别：要点#21 + #3
- 位置：document.py acl(706-716)、publish/unpublish(739-760)、subscribe/unsubscribe(763-830)
- Java 对照：`DocumentResource.java:686-711 / 646-684 / 217-291`（均 204）
- 证据：6 端点 Python 返回 200+body，Java 返回 204。
- 结论与建议：改 204。

## 问题 D-6
- 严重级：HIGH
- 类别：要点#17
- 位置：document.py 第729行后（share 仅 GET 缺 POST）
- Java 对照：`DocumentResource.java:616-643`（createSharedDocument）
- 证据：缺 POST /share（创建分享链接，含 password/expireDate）。
- 结论与建议：补 POST 端点。

## 问题 D-7
- 严重级：HIGH
- 类别：要点#2 + #3
- 位置：`app/routers/document.py:623-652`（new_version）
- Java 对照：`DocumentResource.java:347-402`（createNewDocumentVersion）
- 证据：Python 解析了 role_mapping→user/group_role_mapping 但调用 create_new_version 时未传（静默丢弃）。Java 明确传递。
- 结论与建议：连线 user_role_mapping/group_role_mapping（签名已支持）。

## 问题 D-8
- 严重级：HIGH
- 类别：要点#3（硬编码桩）
- 位置：`app/routers/document_templates.py:136-139`
- Java 对照：`DocumentTemplateResource.java:173-209`
- 证据：`if "attributeTemplates" in body: pass` / `if "lovs"... : pass`。Java 完整持久化。
- 结论与建议：实现 instanceattributetemplate 写逻辑。

## 问题 D-9
- 严重级：MEDIUM
- 类别：要点#4（级联删除）
- 位置：`app/services/document_manager.py:978-980`（delete_template）
- 证据：仅 db.delete(t)，未清理 documentmastertemplate_binres/BinaryResource+vault/documentmastertemplate_attr/instanceattributetemplate/acl 等。
- 结论与建议：补级联删除。

## 问题 D-10
- 严重级：MEDIUM
- 类别：要点#1（裸 SQL 语义偏差）
- 位置：`app/services/document_manager.py:897-904`（list_folders）→ folders.py:23-41
- Java 对照：`FolderResource.java:171-176`（getRootFolders 只返回直接子节点）
- 证据：Python 无 parent_path 时返回所有 `ws/` 前缀 folder（含深层嵌套），子文件夹污染根列表。
- 结论与建议：只查 parentfolder_completepath = workspaceId 的直接子。

## 问题 D-11
- 严重级：MEDIUM
- 类别：要点#6（权限检查）
- 位置：`app/routers/document.py:739-760`（publish/unpublish）
- 证据：Java 内部有写权限检查，Python 无任何 ACL 检查 → 权限绕过。
- 结论与建议：加 check_write_access。

## 问题 D-12
- 严重级：MEDIUM
- 类别：要点#1（target_workspace_id 错误）
- 位置：`app/services/document_manager.py:696-700`（update_iteration 写 documentlink）
- 证据：`target_workspace_id` 恒设为当前 ws，未从 body 提取。跨 ws 链接文档时错误。
- 结论与建议：从 ld.get("workspaceId") 提取。

## 问题 D-13（LOW）
- `app/routers/folders.py:45-48` 重复路由装饰器，删除即可。

## 已排除
- documentlink 缺 id → SERIAL 误报。documentbaseline 归波2。

## 小结
| 严重级 | 数量 |
|--------|------|
| CRITICAL | 4 | D-1~D-4 |
| HIGH | 4 | D-5~D-8 |
| MEDIUM | 4 | D-9~D-12 |
| LOW | 1 | D-13 |

整体：覆盖约 35/39 端点(90%)，核心 CRUD/checkout/release/newVersion 基本对齐。风险：checkout 深拷贝遗漏(D-1)、update_iteration 缺 instanceAttributes(D-3)、4 文件端点缺失(D-2)。优先 D-1/D-2/D-3。
