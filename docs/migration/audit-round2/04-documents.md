# [Documents] 审计报告（域4）

> 第二轮迁移代码审计 ｜ 只读代码对比 ｜ 基准 workspace = GD50

**总体结论**：路由与基本 CRUD 覆盖完整，但权限检查、DTO 字段、文件夹防护、模板删除级联缺陷较多。1 CRITICAL / 7 HIGH / 6 MED / 2 LOW（经独立复核修订）。

---

## 问题 P4-01
- 严重级：CRITICAL
- 复核：CONFIRMED。_doc_to_dict 的 attachedFiles 硬编码 []，它是 GET /documents/{key} 唯一序列化路径（被 32 处调用），instanceAttributes/linkedDocuments 都查了独漏附件。维持 CRITICAL。
- 类别：清单#2 + #11
- 文件：`app/routers/document.py:131`（_doc_to_dict）
- Java对照：`DocumentManagerBean.java:932-940`
- 证据：iteration 的 `attachedFiles` 硬编码 `[]`，从不查 documentiteration_binres+binaryresource（update_iteration 却查了）。GET /documents/{key} 附件永远为空。
- 建议修复：_doc_to_dict 中查询填充 attachedFiles。

## 问题 P4-02
- 严重级：HIGH
- 复核：CONFIRMED。release 缺 checkDocumentRevisionWriteAccess（Java 第一行调）。
- 类别：清单#6（权限检查）
- 文件：`app/services/document_manager.py:753-766`（release）
- Java对照：`DocumentManagerBean.java:1742-1743`（checkDocumentRevisionWriteAccess）
- 证据：release 缺写权限检查，任何用户可释放任意文档。
- 建议修复：开头加 check_write_access。

## 问题 P4-03
- 严重级：MED（原 HIGH，复核调整）
- 复核：SEVERITY-ADJUST→MED。undo_checkout 只允许本人属实，但 Java 允许 admin 强制撤销——Python 更严，是功能缺陷（admin 无法代操作）而非安全漏洞。
- 类别：清单#6
- 文件：`app/services/document_manager.py:673-675`（undo_checkout）
- Java对照：`DocumentManagerBean.java:1041`
- 证据：只检查 checkout_user_login，缺工作区写权限检查。
- 建议修复：加 write access 检查。

## 问题 P4-04
- 严重级：HIGH
- 复核：CONFIRMED。move_document 端点+service 均无权限检查（Java 有 write+folder+home 检查）。
- 类别：清单#6
- 文件：`app/routers/document.py:726-733`（move_document）
- Java对照：`DocumentManagerBean.java:855`
- 证据：move_document 端点与 service 均无权限检查，任何用户可移动任意文档。
- 建议修复：加 write access 检查。

## 问题 P4-05
- 严重级：HIGH
- 复核：CONFIRMED。delete_folder 缺 isAnotherUserHomeFolder/isRoot/isHome 保护，可删根/他人 home。
- 类别：清单#6 + #4
- 文件：`app/services/document_manager.py:1079-1094`（delete_folder）、`folders.py:117-123`
- Java对照：`DocumentManagerBean.java:1104-1117`
- 证据：缺 isAnotherUserHomeFolder/isRoot/isHome 三项保护，可删根/他人 home 文件夹引发级联损毁。
- 建议修复：加三项检查。

## 问题 P4-06
- 严重级：HIGH
- 复核：CONFIRMED。move_folder 缺 home/root/跨工作区四重保护。
- 类别：清单#6
- 文件：`app/routers/folders.py:76-104`（move_folder）
- Java对照：`DocumentManagerBean.java:1148-1183`
- 证据：只查 workspace write，缺 home/root/跨工作区检查。
- 建议修复：加 home/root + 跨工作区目标验证。

## 问题 P4-07
- 严重级：HIGH
- 复核：CONFIRMED。delete_template 直接 DELETE acl 未先删 acluserentry/aclusergroupentry；DB 确认两 FK 无 CASCADE，FK 500。
- 类别：清单#4 + #5
- 文件：`app/services/document_manager.py:1166-1168`（delete_template ACL 清理）
- Java对照：`DocumentManagerBean.java:1255`（JPA cascade）
- 证据：直接 `DELETE FROM acl`，但 acluserentry/aclusergroupentry FK 引用 acl.id 无 CASCADE，未先删子表 → FK 违规 500。
- 建议修复：先删 acluserentry/aclusergroupentry。

## 问题 P4-08
- 严重级：HIGH
- 复核：CONFIRMED。update_doc_acl 缺 hasEntries→removeACL 分支 + 缺 admin/author 权限检查。
- 类别：清单#6 + #17
- 文件：`app/routers/document.py:711-723`（update_doc_acl）
- Java对照：`DocumentResource.java:697-711`、`DocumentManagerBean.java:406-421`
- 证据：Java 有 hasEntries 分支（空 ACL 时 removeACL），Python 总是 apply_acl 从不移除；且端点无 admin/author 权限检查。
- 建议修复：加 hasEntries 分支 + 权限检查。

## 问题 P4-09
- 严重级：HIGH
- 复核：CONFIRMED。inverse_path_link 缺 partLinksList/serialNumber（Java findProductByPathMaster+decodePath）。
- 类别：清单#2
- 文件：`app/routers/document.py:464-484`（inverse_path_link）
- Java对照：`DocumentResource.java:828-868`
- 证据：Python 只返回 {id,path}，缺 partLinksList 和 serialNumber（Java 用 findProductByPathMaster+decodePath 填充）。
- 建议修复：实现 findProductByPathMaster+decodePath。

## 问题 P4-10
- 严重级：MED
- 类别：清单#2
- 文件：`app/schemas/document/document_revision.py:19`（routePath）
- Java对照：`DocumentRevisionDTO.java:105`（String）
- 证据：Java routePath 是 String（completePath），Python 是 list of dict。
- 建议修复：确认前端，必要时改 Optional[str]。

## 问题 P4-11
- 严重级：MED
- 类别：清单#17
- 文件：`app/routers/folders.py:135-149`（create_in_folder）
- Java对照：`FolderResource.java:112-151`
- 证据：忽略 description/acl/roleMapping，仅传 reference/title/templateId/workflowModelId。
- 建议修复：解析并传 description/acl/roleMapping。

## 问题 P4-12
- 严重级：MED
- 类别：清单#2
- 文件：`app/routers/document_templates.py:108-121`（create）
- Java对照：`DocumentTemplateResource.java:146-171`
- 证据：不解析 attributesLocked，创建模板时永远默认值。
- 建议修复：解析并传 attributesLocked。

## 问题 P4-13
- 严重级：MED
- 类别：清单#3（NameError 崩溃）
- 文件：`app/routers/document_templates.py:35-50`、`82-96`（list_templates/get_template）
- Java对照：`DocumentTemplateResource.java:81-93`
- 证据：t.acl_id 非空但 ACL 行不存在时，user_entries/group_entries 未定义 → NameError 500；且 userGroupEntriesMap 硬编码 {}。
- 建议修复：查询移到 if 外或 None 时置空列表。

## 问题 P4-14
- 严重级：MED
- 类别：清单#14（事务）
- 文件：`app/routers/document_files.py:102`、`document_template_files.py:102`
- 证据：循环内每文件 commit，中途失败留半成品；Java 方法结束统一提交。
- 建议修复：commit 移到循环外。

## 问题 P4-15 / P4-16
- 严重级：LOW
- 类别：清单#2
- 证据：iteration id 逻辑一致（冗余 version）；tags String[] 与 List[str] 格式一致。已核对一致，无需修复。

---

## 已核对一致的要点
- #1 裸 SQL：checkoutuser_login 正确用 ORM 属性；表名列名一致；documentlink.id 自增告警为假报。
- #5 dtype：_copy_instance_attributes/_copy_template_instance_attrs/update_iteration 三路径均写 dtype。
- #8 NULL 容忍：日期字段有 None 保护；checkOutUser/releaseAuthor/obsoleteAuthor 仅非空时添加。
- #9 深拷贝：checkout/create_new_version 创建新 instanceattribute/BinaryResource 行。
- #10 vault 路径：`{ws}/documents/{docId}/{ver}/{iter}/{file}` 无 geometry/，一致。
- #15 路由：与 DocumentResource/DocumentsResource/FolderResource/DocumentTemplateResource 对齐。
- #18 GD50：31 条 doc 记录 0 附件，SQL/序列化正常。
