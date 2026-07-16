# Round 5 Audit — Domain 4: Documents

> 日期: 2026-07-16
> 审计范围: `document_manager.py` (service), `document.py`, `folders.py`, `document_templates.py` (routers), `DocumentTemplateDTO` (schema)
> 对照基准: Java `DocumentManagerBean.java`, `DocumentResource.java`, `FolderResource.java`, `DocumentMasterTemplateDTO.java`

---

## 审计结果总览

| 级别 | 数量 | 状态 |
|------|------|------|
| HIGH | 2 | ✅ 已修复 |
| MED | 2 | ✅ 已修复 |
| LOW | 1 | ⏳ 延迟（另行排期） |

---

## 已修复项

### P5-4-1 (HIGH): `create_new_version` 缺失写权限检查

**文件**: `document_manager.py:917`
**Java 对照**: `DocumentManagerBean.java:1431` — `checkWorkspaceWriteAccess`

**问题**: `create_new_version` 方法未检查用户写权限，无权限用户可调用 `PUT /documents/{doc_key}/newVersion` 创建新版本。

**修复**: 在 `get_revision` 之后、`checkout_user_login` 判断之前新增：
```python
from app.services.factory.acl_factory import check_write_access
if not check_write_access(db, pr.acl_id, user_login, False, workspace_id=ws):
    raise AccessRightException("AccessRightException", user_login)
```

---

### P5-4-2 (HIGH): `rename_put` 路由缺失工作区写权限检查

**文件**: `folders.py:85`
**Java 对照**: `DocumentManagerBean.java:1153` — `checkWorkspaceWriteAccess`

**问题**: `PUT /workspaces/{ws}/folders/{folder_path}` (rename) 端点未调用 `_check_workspace_write_access`，任何认证用户均可重命名任意文件夹。

**修复**: 在函数体开头新增 `_check_workspace_write_access(db, ws, current_user.login)`，与同文件其他写端点一致。

---

### P5-4-3 (MED): `DocumentTemplateDTO` 缺失 `workflowModelId` + `build_template_dto` 未填充字段

**文件**: `document_master_template.py`, `document_manager.py:2186`

**问题**:
1. `DocumentTemplateDTO` schema 缺少 `workflowModelId` 字段，Java 响应含此字段，`extra='forbid'` 下会触发 500。
2. `build_template_dto` 不输出 `modificationDate`、`workflowModelId`，且 `attributeTemplates` 始终为空列表。

**修复**:
1. schema 新增 `workflowModelId: Optional[str] = None`
2. `build_template_dto` 新增 `modificationDate`、`workflowModelId` 输出
3. `build_template_dto` 新增 SQL 查询 `instanceattributetemplate` 填充 `attributeTemplates`

---

### P5-4-4 (MED): `create_template` 静默丢弃 `attribute_templates` 参数

**文件**: `document_manager.py:1258`

**问题**: `create_template` 方法接收 `attribute_templates` 参数但未处理，导致创建模板时传入的属性模板被静默丢弃。

**修复**: 新增属性模板插入逻辑（INSERT `instanceattributetemplate` + `documentmastertemplate_attr`），与 `update_template_with_attrs` 风格一致。

---

## 延迟项

### P5-4-5 (LOW): `create_in_folder` 缺失文件夹级写权限检查

**文件**: `folders.py:112`

**说明**: `create_document` 已有 workspace 级写权限检查（`document_manager.py:64-66`），但 Java 的 `createDocumentRevision` 还有 `checkFolderWritingRight` 文件夹级检查。新增文件夹级 ACL 检查函数需额外开发，列为 LOW 优先级延迟。

---

## Round 4→5 回归验证

Round 4 的 14 个 issue（含 CRITICAL P4-01 attachedFiles）在本轮确认均已关闭，无回归。

---

## 修改文件清单

| 文件 | 变更 |
|------|------|
| `docdoku-plm-server-py/app/services/document_manager.py` | P5-4-1: create_new_version 补写权限; P5-4-3: build_template_dto 补全字段; P5-4-4: create_template 处理 attribute_templates |
| `docdoku-plm-server-py/app/routers/folders.py` | P5-4-2: rename_put 补工作区写权限 |
| `docdoku-plm-server-py/app/schemas/document/document_master_template.py` | P5-4-3: DocumentTemplateDTO 补 workflowModelId |
