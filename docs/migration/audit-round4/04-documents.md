# 域4 Documents 文档 审计报告（第4轮）

> 生成日期：2026-07-12 ｜ 范围：`docdoku-plm-server-py` 文档迁移代码 vs Java/Payara
> 方法：explore subagent 逐端点对照 + information_schema 核实 + GD50 验证
> 基准 workspace = GD50 ｜ **只读审计，未做任何修复**

## 结论
**0 CRITICAL / 2 HIGH / 1 MED / 1 LOW**。第2轮 14 项问题（含 P4-01 CRITICAL）在第3轮重构中**全部闭环**。本轮新发现 2 个 HIGH（mark_obsolete + tags 端点缺写权限）。

---

## HIGH

### P4-NEW1 mark_obsolete 缺写权限检查（权限绕过）
- 严重级：HIGH
- 类别：清单#6（权限检查逐行对比）
- 文件：`app/services/document_manager.py:899-908`（mark_obsolete） | Java对照：`DocumentManagerBean.java:1766` 入口首行 `checkDocumentRevisionWriteAccess(pRevisionKey)`
- 证据：Python `mark_obsolete` 从 `get_revision` 起，无写权限检查。任何登录用户可 `PUT /workspaces/{ws}/documents/{doc_key}/obsolete` 将任意文档标记 obsolete。
- 建议修复：`get_revision` 之后、status 检查之前加 `check_write_access`（对齐 Java NotAllowedException65）。
- 与前两轮关系：新发现（第2轮未覆盖此端点）。

### P4-NEW2 文档 tags 端点（set_tags/add_tag/remove_tag）缺写权限检查
- 严重级：HIGH
- 类别：清单#6
- 文件：`app/services/document_manager.py:970-985`(set_tags)、`987-1002`(add_tag)、`1004-1010`(remove_tag) | Java对照：`DocumentManagerBean.java:964` saveTags → `checkDocumentRevisionWriteAccess`；`1016` removeTag 同
- 证据：三方法均缺写权限检查，router 层（`document.py:186-229`）也未检查。任何登录用户可改任意文档标签。（与域1 P1-13 remove_tag 同类系统性缺口）
- 建议修复：三方法入口各加 `check_write_access(db, pr.acl_id, user_login, False, workspace_id=ws)`。
- 与前两轮关系：新发现。

---

## MED

### P4-NEW3 create_document 缺写权限检查
- 严重级：MED
- 类别：清单#6
- 文件：`app/services/document_manager.py:60-137`（create_document） | Java对照：`DocumentManagerBean.createDocumentMaster` 内部 `checkWorkspaceWriteAccess`
- 证据：Python `create_document` 无 `check_write_access`；router 层 `documents.py:115-132`、`folders.py:113-139` 也未检查（仅 folders.py:57/68 文件夹创建路径显式调了 `_check_workspace_write_access`，文档创建未查）。攻击面：仅 GET 可达工作区的用户可创建文档。
- 建议修复：`create_document` 入口加 `check_write_access(db, None, user_login, False, workspace_id=ws)`。
- 与前两轮关系：新发现。

---

## LOW

### P4-NEW4 build_template_dto attachedFiles 硬编码 []
- 严重级：LOW
- 类别：清单#3（硬编码桩）
- 文件：`app/services/document_manager.py:2173`（build_template_dto） | Java对照：`DocumentMasterTemplate.getAttachedFiles()` → DocumentTemplateDTO.attachedFiles
- 证据：`build_template_dto:2173` 硬编码 `"attachedFiles": []`，从不查 `documentmastertemplate_binres`+`binaryresource`；模板附件上传/下载/删除端点均已实现，但 GET 模板 DTO 永远空附件。（与 P4-01 同类但不同实体）
- 建议修复：查询填充，参考 `_query_attached_files` 逻辑。
- 与前两轮关系：新发现。

---

## 第2轮历史问题复核（全部闭环，本轮确认）
| 编号 | 原级 | 新代码位置 | 结论 |
|------|------|-----------|------|
| P4-01 | CRITICAL | `_build_iteration_dict:1517`→`_query_attached_files:1476-1496` 查 documentiteration_binres+binaryresource | ✅ 已修复 |
| P4-02 | HIGH | `release:776` check_write_access | ✅ |
| P4-04 | HIGH | `move_document:1146` check_write_access | ✅ |
| P4-05 | HIGH | `delete_folder:1212-1217` root/home/他人home 三重保护 | ✅ |
| P4-06 | HIGH | `move_folder:2099-2111` home/root/跨工作区四重保护 | ✅ |
| P4-07 | HIGH | `delete_template:1302-1308` 先删 acluserentry+aclusergroupentry 再删 acl | ✅ |
| P4-08 | HIGH | `update_acl:1928-1948` admin/author + hasEntries 分支（空 ACL removeACL） | ✅ |
| P4-09 | HIGH | `get_inverse_path_links:1839-1857` 查 prdinstiteration_pathdatamstr + decode_path 填 partLinksList/serialNumber | ✅ |
| P4-03/10/11/12/13/14 | MED | undo_checkout admin 旁路 / routePath 字符串 / role_mapping+template_id / attributes_locked / ACL None 安全 / save_file flush+caller commit | ✅ |

---

## 已核对一致的要点
| 要点 | 结论 |
|------|------|
| 裸SQL表名列名 | documentiteration_binres/documentlink/documentrevision_tag/documentmastertemplate_attr/acluserentry/aclusergroupentry 经 information_schema 核实（documentlink 缺 id 是自增误报） |
| Service层HTTPException | 全部领域异常（AccessRightException/NotAllowedException），无违规 |
| Vault路径 | `{ws}/documents/{doc_id}/{ver}/{it}/{filename}`，无 geometry/ |
| checkout 深拷贝 | `_copy_attached_files`/`_copy_linked_documents`/`_copy_instance_attributes` 新行 |
| delete_revision/folder 级联 | 完整（baseline/逆链接/changeItem 约束检查 + 子表清理 + vault 物理删） |
| DTO字段对齐 | DocumentRevisionDTO 40 字段 = Java；ACLDTO userEntriesMap/userGroupEntriesMap 已填充 |
| 状态码 | 204(DELETE/PUT acl/subscribe)/201(create/upload/share)/200(GET/PUT) |
| GD50冒烟 | GET /workspaces/GD50/documents → 200 |
