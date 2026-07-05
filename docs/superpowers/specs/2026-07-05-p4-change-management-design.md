# 设计：P4 变更管理（Change Issues/Requests/Orders/Milestones）

日期：2026-07-05
状态：设计已确认，待写实现计划
路线图阶段：P4（见 `docs/superpowers/fastapi-migration-roadmap.md`）

## 背景

P0-P3（基础设施/零件/文档/产品结构）已完成。P4 迁移变更管理模块。所有变更表当前为空（未使用过变更功能），实现以代码完整性为先。

## 目标

实现变更管理的 4 类实体（ChangeIssue/ChangeRequest/ChangeOrder/Milestone）的 CRUD + 标签管理，行为与 Payara 一致，前端零改动。

## 范围

**In scope（~30 端点）**：

| 域 | 端点 | 说明 |
|---|---|---|
| Issues CRUD | GET/POST `/changes/issues` + GET/PUT/DELETE `/{id}` | 5 端点 |
| Requests CRUD | GET/POST `/changes/requests` + GET/PUT/DELETE `/{id}` | 5 端点 |
| Orders CRUD | GET/POST `/changes/orders` + GET/PUT/DELETE `/{id}` | 5 端点 |
| Milestones CRUD | GET/POST `/changes/milestones` + GET/PUT/DELETE `/{id}` | 5 端点 |
| 标签管理 | PUT/POST/DELETE `/{id}/tags`（每类 3 个）| 12 端点 |

**Out of scope**：
- `link?q=`（搜索链接）——前端极少使用
- `affected-documents`/`affected-parts`/`affected-issues`/`affected-requests`——DB 全空，返回空集合
- `acl`——P5 权限体系
- `/milestones/{id}/requests|orders`——只读关联，返回空
- Workflow 相关——P5

## 架构

### 新建文件

| 文件 | 职责 | 依赖 |
|------|------|------|
| `app/models/change.py` | ~8 ORM 表（changeissue/changeorder/changerequest/milestone + tag/acl 关联表） | database |
| `app/routers/changes.py` | 全部 ~30 端点（`/workspaces/{ws}/changes/{type}/{id}...`） | change_service |
| `app/services/change_service.py` | 通用 CRUD + 类型特定的创建/更新逻辑 | models/change.py |

### 修改文件

| 文件 | 改动 |
|------|------|
| `app/main.py` | 注册 changes 路由 |
| `docdoku-plm-docker/front/nginx.conf` | 1 条 location 正则块 `^/.../workspaces/[^/]+/changes` |

### Nginx 路由变更

一条正则覆盖全部 46 端点：

```nginx
location ~ ^/docdoku-plm-server-rest/api/workspaces/[^/]+/changes {
    set $backpy "back-py:8000";
    proxy_pass http://$backpy;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
    client_max_body_size 500m;
}
```

### 架构特点

46 端点模式高度重复（4 类型 × 相同 CRUD），service 层用统一模板，路由层直接映射。ACL + affected-* 端点因 DB 全空返回空集合。

### DB 表（全部空）

| 表 | 说明 | 行数 |
|---|---|---|
| `changeissue` | 变更问题 | 0 |
| `changeissue_tag` | 问题标签 | 0 |
| `changeissue_affected_document` | 问题关联文档 | 0 |
| `changeissue_affected_part` | 问题关联零件 | 0 |
| `changeorder` | 变更订单 | 0 |
| `changeorder_tag` | 订单标签 | 0 |
| `changeorder_changerequest` | 订单关联请求 | 0 |
| `changerequest` | 变更请求 | 0 |
| `changerequest_tag` | 请求标签 | 0 |
| `changerequest_changeissue` | 请求关联问题 | 0 |
| `milestone` | 里程碑 | 0 |

## i18n 对齐基线（粗略，计划执行时精读 Java 补齐）

| 场景 | i18n key |
|------|----------|
| 变更项未找到 | `ChangeIssueNotFoundException` / `ChangeRequestNotFoundException` / `ChangeOrderNotFoundException` |
| 里程碑未找到 | `MilestoneNotFoundException` |
| 变更项已存在 | `*AlreadyExistsException` |

i18n 基础设施复用 P1a-align 批次 0 的 `app/core/exceptions.py` + `i18n.py` + `exception_handlers.py`。

## 前端 Model 审计

P4 范围内**无 `.author.name` 嵌套崩溃风险**。`author`/`assignee` 在 Payara DTO 中已是平铺字段（`authorName`/`assigneeName`），前端通过 `model.getAuthorName()` 安全访问。唯一嵌套风险在 workflow 模块（P5 范围）。

## 测试策略

1. **前端 Model 审计**（P3 防御清单 #0，每阶段启动前必做）：读 `change_item.js`/`change_issue.js`/`change_request.js`/`change_order.js`/`milestone.js` 的 `parse()`/`initialize()`/`this.get()`，确认响应必需字段无缺失。P4 范围内 `author`/`assignee` 已平铺为 `authorName`/`assigneeName`，无 `.author.name` 嵌套风险。
2. **单元/集成测试**（真实 DB, TestClient）：每个类型的 CRUD + 错误路径
3. **Payara 对拍**：创建/列表/详情/删除 对比端口 8001 vs 8000
4. **前端实测清单**：建 Issue→创建→编辑→删除→Milestone 全流程

## 执行顺序（遵循标准每阶段工作流）

1. 前端 Model 审计（确认响应必需字段）
2. ORM 建模（`app/models/change.py`）
3. ChangeService CRUD
4. changes 路由
5. **对齐审计**（逐方法对照 Java + 补齐 i18n）
6. **Payara 对拍**（无 diff）
7. **前端实测清单**交用户验收
8. **通过后**切 Nginx 变更路由
9. 更新文档
