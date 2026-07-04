# 设计：P2 文档与文件夹 + 文档模板

日期：2026-07-05
状态：设计已确认，待写实现计划
路线图阶段：P2（见 `docs/superpowers/fastapi-migration-roadmap.md`）

## 背景

P0（基础设施）、P1a-core（零件 CRUD）、P1a-align（行为对齐）、P1b（零件文件/转换/状态/搜索）已完成。P2 迁移文档与文件夹模块，完成后 Payara 退出文档相关职责。

## 目标

在 FastAPI 实现文档的 4 个功能域，行为与 Payara 一致，前端零改动：
1. 文档 CRUD（创建/删除/签出/签入/发布/废弃/标签/搜索）
2. 文档文件（上传/下载）
3. 文件夹 CRUD
4. 文档模板 CRUD（含模板文件）

## 范围

**In scope（~30 端点）**：

| 域 | 端点 | 说明 |
|---|---|---|
| 文档 CRUD | GET/POST `/documents` + GET `/count` + GET `/{id}-{ver}` + DELETE `/{id}-{ver}` | 列表、创建、详情、删除 |
| 文档签出 | PUT `/{id}-{ver}/checkout\|checkin\|undocheckout` | 与零件一致 |
| 文档状态 | PUT `/{id}-{ver}/release\|obsolete\|newVersion` | 与零件一致 |
| 文档迭代 | PUT `/{id}-{ver}/iterations/{iter}` | 更新迭代属性 |
| 文档标签 | PUT/POST/DELETE `/{id}-{ver}/tags` | 增删改 |
| 文档搜索 | GET `/documents/search` | DB LIKE MVP（`documentmaster.title`/`doc_id`） |
| 文档文件 | POST/GET `/api/files/{ws}/documents/{id}/{ver}/{iter}/{file}` | 上传下载 |
| 文件夹 | GET/POST/PUT/DELETE `/folders` + 子文件夹路径 | 增删改查 |
| 文档模板 | GET/POST/PUT/DELETE `/document-templates` + 文件上传下载 | CRUD+文件 |

**Out of scope**：
- 基线（DocumentBaselines / baselined / documentbaseline）——DB 全空，需要时再做
- 通知订阅（subscribeToIterationChangeEvent 等）——P5
- 反向链接查询（inverse-document-link / inverse-part-link）——DB 全空
- ACL / 共享 / publish（sharedentity / public shared）——P5 权限体系
- 文件夹内创建文档（`POST /folders/{id}/documents`）——前端暂无此流程
- 文档移动（move）——用文件夹操作可替代

## 架构

### 新建文件

| 文件 | 职责 | 依赖 |
|------|------|------|
| `app/models/document.py` | ~15 张 ORM 表（documentmaster/revision/iteration/binres/link/folder/template 相关） | database |
| `app/routers/documents.py` | DocumentResource + DocumentsResource 端点（`/workspaces/{ws}/documents`） | document_service |
| `app/routers/folders.py` | FolderResource 端点（`/workspaces/{ws}/folders`） | document_service |
| `app/routers/document_files.py` | 文件上传下载端点（`/api/files/{ws}/documents/`） | document_service |
| `app/routers/document_templates.py` | DocumentTemplateResource 端点 + 模板文件 | document_service |
| `app/services/document_service.py` | DocumentManagerBean 对应业务逻辑 | models.document |

### 修改文件

| 文件 | 改动 |
|------|------|
| `app/main.py` | 注册 4 个新路由 |
| `docdoku-plm-docker/front/nginx.conf` | 新增 documents / folders / document-templates / files/documents 路由块 |

### Nginx 路由变更

新增 3 个路由块，在兜底 Payara 之前：

```nginx
# P2：文档端点
location ~ ^/docdoku-plm-server-rest/api/workspaces/[^/]+/documents {
    set $backpy "back-py:8000";
    proxy_pass http://$backpy;
    ...
}

# P2：文件夹端点
location ~ ^/docdoku-plm-server-rest/api/workspaces/[^/]+/folders {
    set $backpy "back-py:8000";
    proxy_pass http://$backpy;
    ...
}

# P2：文档模板端点
location ~ ^/docdoku-plm-server-rest/api/workspaces/[^/]+/document-templates {
    set $backpy "back-py:8000";
    proxy_pass http://$backpy;
    ...
}

# P2：文档文件端点
location ~ ^/docdoku-plm-server-rest/api/files/[^/]+/documents {
    set $backpy "back-py:8000";
    ...
}
```

### DB 表概览（24 张，当前仅 folder 有 4 行数据）

| 表 | 说明 | 行数 |
|---|---|---|
| documentmaster | 文档主数据 | 0 |
| documentrevision | 文档版本 | 0 |
| documentiteration | 文档迭代 | 0 |
| documentiteration_binres | 迭代二进制文件 | 0 |
| documentiteration_documentlink | 迭代→文档链接 | 0 |
| documentlink | 文档链接 | 0 |
| documentmastertemplate | 模板主数据 | 0 |
| documentmastertemplate_binres | 模板文件 | 0 |
| documentrevision_tag | 文档标签 | 0 |
| **folder** | **文件夹** | **4** |
| （其余表均为 0 行） | | |

## i18n 对齐基线（粗略，计划执行时精读 Java 补齐）

### 共享 key（与零件一致，复用已有 infrastructure）

| 场景 | i18n key |
|------|----------|
| 非当前用户撤签 | `NotAllowedException19` |
| 非当前用户签入 | `NotAllowedException20` |
| 已签出 | `NotAllowedException37` |
| 已发布/废弃不能签出 | `NotAllowedException47` |
| 文件归属校验 | `NotAllowedException4` |

### 文档特有 key

| 场景 | i18n key |
|------|----------|
| 文档已存在 | `DocumentMasterAlreadyExistsException` |
| 文档版本已存在 | `DocumentRevisionAlreadyExistsException` |
| 文档未找到 | `DocumentRevisionNotFoundException` |
| 文档迭代未找到 | `DocumentIterationNotFoundException` |
| 模板已存在 | `DocumentMasterTemplateAlreadyExistsException` |
| 模板未找到 | `DocumentMasterTemplateNotFoundException` |
| 文件夹已存在 | `FolderAlreadyExistsException` |
| 文件夹未找到 | `FolderNotFoundException` |
| 系统/他人文件夹删除 | `NotAllowedException21` |
| 跨工作区移动文件夹 | `NotAllowedException23` |
| 私有父文件夹 | `NotAllowedException33` |
| 非自己的文件删除 | `NotAllowedException24` |
| 非自己的文件重命名 | `NotAllowedException29` |
| 模板属性锁定 | `NotAllowedException44` |
| 文件夹已冻结 | `NotAllowedException7` |
| 签出文档的任务操作 | `NotAllowedException16` |

### 审计执行

计划执行阶段派 explore agent 逐方法对照 `DocumentManagerBean.java`，补齐遗漏的校验点和 i18n key。i18n 基础设施复用 P1a-align 批次 0 的 `app/core/exceptions.py` + `i18n.py` + `exception_handlers.py`，不新建。

## 搜索（DB MVP）

与 P1b 一致：SQLAlchemy `ilike` 模糊匹配 `documentmaster.title` 和 `documentmaster.doc_id`。ES 全文搜索推到 P5 后独立子项目。

## 测试策略

1. **单元/集成测试**（真实 DB, TestClient）：每个方法错误路径断言 i18n key 翻译 + HTTP 状态码
2. **Payara 对拍**：文档列表/详情/删除/签出/文件夹 先用 `compare_with_payara.py` 对比通过，再切 Nginx
3. **前端实测清单**（交用户）：建文档→签出签入→发布废弃→上传下载→文件夹增删→模板 CRUD→搜索

## 执行顺序（遵循标准每阶段工作流）

1. ORM 建模（`app/models/document.py`）
2. 文档 CRUD + 签出签入 + 状态 + 标签 + 搜索
3. 文件上传下载
4. 文件夹 CRUD
5. 文档模板 CRUD
6. **对齐审计**（逐方法对照 Java + 补齐 i18n）
7. **Payara 对拍**（无 diff 后进入下一步）
8. **前端实测清单** 交用户验收
9. **通过后** 切 Nginx 文档/文件夹/模板/文件路由
10. 更新 REMINDERS + CHANGELOG + 路线图状态
