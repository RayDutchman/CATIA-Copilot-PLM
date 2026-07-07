# P5 工作流与权限 设计文档

> **日期**：2026-07-05
> **状态**：已批准
> **前置**：P0-P4 已完成

---

## 1. 范围

完整迁移 Payara 后端剩余的工作流与权限模块到 FastAPI，共 **66+ 端点**，覆盖 6 个功能域：

| 域 | 端点数 | 说明 |
|---|---|---|
| A. 用户/账号/组管理 | ~24 | UserResource(6) + UserGroupResource(5) + WorkspaceMembership(4) + WorkspaceResource 用户管理(9) + AccountResource(5，me 已有) |
| B. 工作流 | 17 | WorkflowModel(6) + Workflow(2) + WorkspaceWorkflow(4) + Task(5) |
| C. ACL/角色 | 13 | RoleResource(5) + 给 parts/documents/products/templates 补齐 ACL 端点(~8) |
| D. 通知 | 5 | ModificationNotification(1) + 标签订阅(4) |
| E. Webhook | 5 | WebhookResource(5) |
| F. Auth 补全 | 5 | recovery/recover/logout/providers/{id}/oauth |

**决策**：完整迁移全部 P5（含空表功能），单 spec 单 plan。

---

## 2. 文件组织（方案 A：按功能域分文件）

### 新建文件

| 文件 | 职责 |
|------|------|
| `app/models/user_mgmt.py` | UserGroup、Credential（Account/UserGroupMapping 已有，补充 relationships） |
| `app/models/security.py` | ACL、AclUserEntry、AclUserGroupEntry、Role、role_user、role_usergroup 关联表 |
| `app/models/workflow.py` | WorkflowModel、Workflow、Activity（单表继承）、Task、Webhook、WebhookApp |
| `app/models/notification.py` | ModificationNotification、IterationChangeSubscription、StateChangeSubscription |
| `app/services/user_mgmt_service.py` | 用户/组/成员资格/账号管理 |
| `app/services/security_service.py` | ACL CRUD + Role CRUD + 权限检查 |
| `app/services/workflow_service.py` | 工作流模板/实例/任务管理 |
| `app/services/notification_service.py` | 通知确认 + 标签订阅 |
| `app/services/acl_helper.py` | 共享 ACL upsert 纯函数（被各 resource 复用） |
| `app/routers/users.py` | 用户/组/成员资格端点 |
| `app/routers/accounts.py` | 账号端点（create/update/workspaces） |
| `app/routers/workflows.py` | 工作流模板/实例/任务端点 |
| `app/routers/roles.py` | 角色端点 |
| `app/routers/notifications.py` | 通知端点 |
| `app/routers/webhooks.py` | Webhook 端点 |

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `app/routers/auth.py` | 补 recovery/recover/logout/providers/{id}/oauth |
| `app/routers/parts.py` | 补 `PUT /{part_key}/acl` 端点 |
| `app/routers/documents.py` | 补 `PUT /{doc_key}/acl` 端点 |
| `app/routers/products.py` | 补 `PUT /{ciId}/configurations/{pcId}/acl` 等端点 |
| `app/routers/part_files.py` 或 `document_templates.py` | 补模板 ACL 端点 |
| `app/main.py` | 注册 6 个新路由 |
| `docdoku-plm-docker/front/nginx.conf` | 新增 10+ location 块 |

---

## 3. ORM 建模

### 3.1 `app/models/user_mgmt.py`

```python
class UserGroup(Base):
    __tablename__ = "usergroup"
    id = Column(String, primary_key=True)  # 组 ID
    workspace_id = Column(String, primary_key=True)

class Credential(Base):
    __tablename__ = "credential"
    login = Column(String, primary_key=True, ForeignKey("account.login"))
    password = Column(String)  # MD5 hex
```

注：`Account`、`UserGroupMapping`、`User`(userdata) 已在 `models/auth.py` 中建模。P5 给 `User` 补充 group relationship。

### 3.2 `app/models/security.py`

```python
class ACL(Base):
    __tablename__ = "acl"
    id = Column(Integer, primary_key=True, autoincrement=True)
    enabled = Column(Boolean)

class AclUserEntry(Base):
    __tablename__ = "acluserentry"
    acl_id = Column(Integer, ForeignKey("acl.id"), primary_key=True)
    principal_login = Column(String, primary_key=True)
    principal_workspace_id = Column(String, primary_key=True)
    permission = Column(String)  # FORBIDDEN / READ_ONLY / FULL_ACCESS

class AclUserGroupEntry(Base):
    __tablename__ = "aclusergroupentry"
    acl_id = Column(Integer, ForeignKey("acl.id"), primary_key=True)
    principal_id = Column(String, primary_key=True)
    principal_workspace_id = Column(String, primary_key=True)
    permission = Column(String)

class Role(Base):
    __tablename__ = "role"
    name = Column(String, primary_key=True)
    workspace_id = Column(String, primary_key=True)
    # 关联表 role_user / role_usergroup 通过 Table 定义
```

**role_user 关联表**：
```python
role_user = Table("role_user", Base.metadata,
    Column("role_name", String, primary_key=True),
    Column("role_workspace_id", String, primary_key=True),
    Column("user_login", String, primary_key=True),
    Column("user_workspace_id", String, primary_key=True),
    ForeignKeyConstraint(["role_name", "role_workspace_id"], ["role.name", "role.workspace_id"]),
    ForeignKeyConstraint(["user_login", "user_workspace_id"], ["userdata.login", "userdata.workspace_id"]),
)
```

**role_usergroup 关联表**：同理，关联 `role` 和 `usergroup`。

### 3.3 `app/models/workflow.py`

```python
class WorkflowModel(Base):
    __tablename__ = "workflowmodel"
    id = Column(String, primary_key=True)  # 含 workspace_id 复合 PK
    workspace_id = Column(String, primary_key=True)
    finalLifecycleState = Column("finallifecyclestate", String)
    creationdate = Column(DateTime)
    author_workspace_id = Column(String)
    author_login = Column(String)
    acl_id = Column(Integer, ForeignKey("acl.id"))

class Workflow(Base):
    __tablename__ = "workflow"
    id = Column(Integer, primary_key=True)
    aborteddate = Column(DateTime)
    finallifecyclestate = Column(String)

class Activity(Base):
    __tablename__ = "activity"
    step = Column(Integer, primary_key=True)
    workflow_id = Column(Integer, ForeignKey("workflow.id"), primary_key=True)
    dtype = Column(String)  # 继承鉴别器: SEQUENTIAL / PARALLEL
    lifecyclestate = Column(String)
    taskstocomplete = Column(Integer)
    # SQLAlchemy 单表继承: polymorphic_on=dtype
    __mapper_args__ = {
        "polymorphic_identity": "SEQUENTIAL",
        "polymorphic_on": dtype,
    }

class Task(Base):
    __tablename__ = "task"
    num = Column(Integer, primary_key=True)
    activity_step = Column(Integer, primary_key=True)
    workflow_id = Column(Integer, primary_key=True)
    title = Column(String)
    instructions = Column(Text)
    status = Column(Integer)  # 0=TODO, 1=IN_PROGRESS, 2=APPROVED, 3=REJECTED
    worker_login = Column(String)
    worker_workspace_id = Column(String)
    duration = Column(Integer)
    signature = Column(Text)
    closuredate = Column(DateTime)
    closurecomment = Column(String)
    startdate = Column(DateTime)
    targetiteration = Column(Integer)
```

**Webhook**：
```python
class WebhookApp(Base):
    __tablename__ = "webhookapp"
    id = Column(Integer, primary_key=True, autoincrement=True)
    dtype = Column(String)  # SIMPLE_HTTP / AWS_SNS
    auth = Column(String)  # BasicAuth header
    method = Column(String)
    uri = Column(String)
    awsaccount = Column(String)
    awssecret = Column(String)
    region = Column(String)
    topicarn = Column(String)

class Webhook(Base):
    __tablename__ = "webhook"
    id = Column(Integer, primary_key=True, autoincrement=True)
    active = Column(Boolean)
    name = Column(String)
    workspace_id = Column(String)
    webhookapp_id = Column(Integer, ForeignKey("webhookapp.id"))
```

### 3.4 `app/models/notification.py`

```python
class ModificationNotification(Base):
    __tablename__ = "modificationnotification"
    id = Column(Integer, primary_key=True, autoincrement=True)
    acknowledged = Column(Boolean)
    acknowledgementcomment = Column(String)
    acknowledgementdate = Column(DateTime)
    ackauthor_workspace_id = Column(String)
    ackauthor_login = Column(String)
    impacted_partrevision_version = Column(String)
    impacted_iteration = Column(Integer)
    impacted_workspace_id = Column(String)
    impacted_partmaster_partnumber = Column(String)
    modified_workspace_id = Column(String)
    modified_partmaster_partnumber = Column(String)
    modified_iteration = Column(Integer)
    modified_partrevision_version = Column(String)

# iterationchangesubscription / statechangesubscription 关联表定义
```

---

## 4. Service 层

### 4.1 `user_mgmt_service.py`

| 方法 | 签名 | 校验 |
|------|------|------|
| `list_users` | `(db, ws) -> list[User]` | — |
| `list_groups` | `(db, ws) -> list[UserGroup]` | — |
| `create_group` | `(db, ws, group_id) -> UserGroup` | EntityAlreadyExists |
| `delete_group` | `(db, ws, group_id)` | 有成员→EntityConstraintException11 |
| `add_user` | `(db, ws, login, group_id?)` | UserNotFound, GroupNotFound |
| `remove_user_from_workspace` | `(db, ws, login)` | — |
| `remove_user_from_group` | `(db, ws, login, group_id)` | — |
| `enable_user` / `disable_user` | `(db, ws, login)` | — |
| `set_admin` | `(db, ws, login)` | — |
| `set_user_access` | `(db, ws, login, access)` | access: READ_ONLY/FULL_ACCESS |
| `list_memberships` | `(db, ws) -> list` | — |
| `create_account` | `(db, login, password, email, name, lang) -> Account` | EntityAlreadyExists |
| `update_account` | `(db, login, fields) -> Account` | — |
| `list_workspaces_for_user` | `(db, login) -> list[Workspace]` | 查 userdata |

### 4.2 `security_service.py`

| 方法 | 用途 |
|------|------|
| `list_roles(ws)` / `list_roles_in_use(ws)` | 列角色 |
| `create_role(ws, name, defaultUsers?, defaultGroups?)` | 建角色 |
| `update_role(ws, name, ...)` | 更新角色默认分配 |
| `delete_role(ws, name)` | 删角色（in-use→EntityConstraintException25） |
| `get_acl(acl_id)` | 读 ACL |
| `update_acl(acl_id, userEntries, groupEntries)` | upsert + delete 模式 |
| `check_write_access(acl_id, user_login, is_admin)` | 权限检查（被各 service 复用） |

**ACL 权限模型**：
- `permission` 枚举：`FORBIDDEN` / `READ_ONLY` / `FULL_ACCESS`
- `acl=None` 或 `acl.enabled=false` → 公开（管理员直接通过）
- 管理员 → 直接通过
- ACL 有 `FULL_ACCESS` 条目匹配用户 → 通过
- 否则 → AccessRightException

### 4.3 `workflow_service.py`

| 方法 | 用途 |
|------|------|
| `list_workflow_models(ws)` / `get_workflow_model(ws, id)` | 查询模板 |
| `create_workflow_model(ws, id, finalState, activities)` | 建模板（含 Activity+Task 嵌套） |
| `update_workflow_model(ws, id, ...)` | 更新模板 |
| `delete_workflow_model(ws, id)` | 删模板（in-use→EntityConstraintException25） |
| `get_workflow_instance(ws, id)` | 查实例（含 activities+tasks 嵌套） |
| `list_workspace_workflows(ws)` | 列运行中的工作流 |
| `create_workspace_workflow(ws, modelId)` | 实例化 |
| `get_task(ws, taskId)` | 查任务 |
| `get_assigned_tasks(ws, login)` | 用户被分配的任务 |
| `process_task(ws, taskId, action, comment, signature)` | 审批/拒绝 |

**process_task MVP 策略**：只记录状态（APPROVED/REJECTED + closure 字段），**不自动推进工作流状态机**。Payara 的 `WorkflowManagerBean.executeTask()` 有 ~200 行推进逻辑（检查当前 activity 所有 task 完成后推进下一步、触发通知等）。前端有手动 relaunch 按钮，MVP 阶段用户手动推进。自动推进打桩 TODO。

### 4.4 `notification_service.py`

| 方法 | 用途 |
|------|------|
| `acknowledge_notification(ws, id, comment, user)` | 确认通知 |
| `list_tag_subscriptions(ws, login/groupId)` | 查标签订阅 |
| `update_tag_subscription(ws, login/groupId, tag, onIter, onState)` | 更新订阅 |
| `delete_tag_subscription(ws, login/groupId, tag)` | 删订阅 |

### 4.5 `acl_helper.py`（共享）

```python
def apply_acl(db, acl_id: int | None, user_entries: dict, group_entries: dict) -> int:
    """upsert ACL entries，返回 acl_id（None 则新建 ACL）"""
```

被 `parts.py`、`documents.py`、`products.py` 等已有路由的 `PUT .../acl` 端点复用。

---

## 5. 路由层

### 5.1 `routers/users.py`（~24 端点）

```
GET    /workspaces/{ws}/users                      list_users
GET    /workspaces/{ws}/users/me                   who_am_i
GET    /workspaces/{ws}/users/admin                get_admin
GET    /workspaces/{ws}/users/{login}/tag-subscriptions
PUT    /workspaces/{ws}/users/{login}/tag-subscriptions/{tagName}
DELETE /workspaces/{ws}/users/{login}/tag-subscriptions/{tagName}
GET    /workspaces/{ws}/groups                     list_groups
GET    /workspaces/{ws}/groups/{gid}/tag-subscriptions
GET    /workspaces/{ws}/groups/{gid}/users
PUT    /workspaces/{ws}/groups/{gid}/tag-subscriptions/{tagName}
DELETE /workspaces/{ws}/groups/{gid}/tag-subscriptions/{tagName}
GET    /workspaces/{ws}/memberships/users
GET    /workspaces/{ws}/memberships/users/me
GET    /workspaces/{ws}/memberships/usergroups
GET    /workspaces/{ws}/memberships/usergroups/me
# WorkspaceResource 内的用户管理端点
GET    /workspaces/{ws}/user-group                 get_user_groups
POST   /workspaces/{ws}/user-group                 create_group
DELETE /workspaces/{ws}/user-group/{gid}           delete_group
PUT    /workspaces/{ws}/add-user                   add_user
PUT    /workspaces/{ws}/admin                      set_admin
PUT    /workspaces/{ws}/user-access                set_user_access
PUT    /workspaces/{ws}/group-access               set_group_access
PUT    /workspaces/{ws}/remove-from-group/{gid}    remove_from_group
PUT    /workspaces/{ws}/remove-from-workspace      remove_from_workspace
PUT    /workspaces/{ws}/enable-user                enable_user
PUT    /workspaces/{ws}/disable-user               disable_user
PUT    /workspaces/{ws}/enable-group               enable_group
PUT    /workspaces/{ws}/disable-group              disable_group
```

⚠️ **尾斜杠双路由**：所有 POST/PUT/DELETE 端点必须注册带 `/` 和不带 `/` 的双路由（前端 Backbone 始终带 `/`）。

### 5.2 `routers/accounts.py`（5 端点）

```
PUT    /accounts/me                                update_account
POST   /accounts/create                             create_account
GET    /accounts/workspaces                         list_workspaces_for_user
PUT    /accounts/gcm                                set_gcm
DELETE /accounts/gcm                                delete_gcm
```

注：`GET /accounts/me` 已在 `auth.py` 中实现为 `/auth/me`。

### 5.3 `routers/workflows.py`（17 端点）

```
# WorkflowModel
GET    /workspaces/{ws}/workflow-models             list
GET    /workspaces/{ws}/workflow-models/{id}        get
POST   /workspaces/{ws}/workflow-models             create
PUT    /workspaces/{ws}/workflow-models/{id}        update
PUT    /workspaces/{ws}/workflow-models/{id}/acl    update_acl
DELETE /workspaces/{ws}/workflow-models/{id}        delete
# Workflow 实例
GET    /workspaces/{ws}/workflow-instances/{id}     get_instance
GET    /workspaces/{ws}/workflow-instances/{id}/aborted  get_aborted_list
# WorkspaceWorkflow
GET    /workspaces/{ws}/workspace-workflows         list
GET    /workspaces/{ws}/workspace-workflows/{id}    get
POST   /workspaces/{ws}/workspace-workflows         create
DELETE /workspaces/{ws}/workspace-workflows/{id}    delete
# Task
GET    /workspaces/{ws}/tasks/{login}/assigned      assigned_tasks
GET    /workspaces/{ws}/tasks/{id}                  get_task
GET    /workspaces/{ws}/tasks/{login}/documents     docs_with_tasks
GET    /workspaces/{ws}/tasks/{login}/parts         parts_with_tasks
PUT    /workspaces/{ws}/tasks/{id}/process          process_task
```

### 5.4 `routers/roles.py`（5 端点）

```
GET    /workspaces/{ws}/roles                       list
GET    /workspaces/{ws}/roles/inuse                 list_in_use
POST   /workspaces/{ws}/roles                       create
PUT    /workspaces/{ws}/roles/{name}                update
DELETE /workspaces/{ws}/roles/{name}                delete
```

### 5.5 `routers/notifications.py`（5 端点）

```
PUT    /workspaces/{ws}/notifications/{id}          acknowledge
# 标签订阅已在 users.py 中（tag-subscriptions 端点）
```

### 5.6 `routers/webhooks.py`（5 端点）

```
GET    /workspaces/{ws}/webhooks                    list
GET    /workspaces/{ws}/webhooks/{id}               get
POST   /workspaces/{ws}/webhooks                    create
PUT    /workspaces/{ws}/webhooks/{id}               update
DELETE /workspaces/{ws}/webhooks/{id}               delete
```

### 5.7 `routers/auth.py` 补全（5 端点）

```
POST   /auth/recovery                               send_password_recovery (SMTP)
POST   /auth/recover                                execute_password_recover
GET    /auth/logout                                 logout (JWT 无状态，返回 204)
GET    /auth/providers/{id}                         get_provider_detail
POST   /auth/oauth                                  oauth_login
```

⚠️ OAuth 需要 OAuth provider 配置表（可能在 DB 中或配置文件）。实现时第一步骤查证。

### 5.8 已有路由补齐 ACL 端点

```
PUT    /workspaces/{ws}/parts/{part_key}/acl        → parts.py
PUT    /workspaces/{ws}/documents/{doc_key}/acl     → documents.py
PUT    /workspaces/{ws}/products/{ciId}/configurations/{pcId}/acl  → products.py
PUT    /workspaces/{ws}/document-templates/{id}/acl → document_templates.py
PUT    /workspaces/{ws}/part-templates/{id}/acl     → part_templates.py（如有）
```

---

## 6. Nginx 路由

新增 location 块（插入在 Payara 兜底之前）：

```nginx
# P5：用户/组/成员资格/角色/工作流/通知/Webhook/账号
location ~ ^/docdoku-plm-server-rest/api/workspaces/[^/]+/(users|groups|memberships|roles|workflow-models|workflow-instances|workspace-workflows|tasks|notifications|webhooks|user-group) {
    set $backpy "back-py:8000";
    proxy_pass http://$backpy;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 300s;
    client_max_body_size 500m;
}

# WorkspaceResource 内的散落用户管理端点
location ~ ^/docdoku-plm-server-rest/api/workspaces/[^/]+/(add-user|admin|user-access|group-access|remove-from-group|remove-from-workspace|enable-user|disable-user|enable-group|disable-group) {
    set $backpy "back-py:8000";
    proxy_pass http://$backpy;
    # ... 同上
}

# 账号
location /docdoku-plm-server-rest/api/accounts {
    set $backpy "back-py:8000";
    proxy_pass http://$backpy;
    # ... 同上
}
```

⚠️ **路由冲突风险**：`/workspaces/{ws}/user-group` 和 `/workspaces/{ws}/users` 都需要切到 back-py，但已有的 parts/documents/products/changes 路由也在同一前缀下。需要确保正则优先级正确——具体路径优先于通配。

---

## 7. 前端 Model 审计 — 崩溃风险

### P0 级崩溃点（必须确保响应字段非 null）

| Model | 崩溃表达式 | 触发条件 |
|-------|-----------|----------|
| ActivityModel | `this.get('taskModels').models` | `taskModels` 为 null |
| 运行时 Task | `task.status.toLowerCase()` | `status` 为 null |
| Aborted Workflow | `abortedWorkflows[k].activities[i].tasks[j].status` | 四层嵌套任意为 null |
| ModificationNotification | `this.getAuthor().name` / `.login` | `author` 为 null |
| WorkspaceUserMembership | `this.getUser().login` / `.name` | `member` 为 null |

### 必需字段清单（按 Model）

**ModificationNotification**：`id`, `impactedPartNumber`, `modifiedPartNumber`, `modifiedPartVersion`, `modifiedPartIteration`, `author`(含 name+login), `acknowledged`

**WorkspaceUserMembership**：`workspaceId`, `member`(含 login+name), `readOnly`

**WorkflowModel**：`id`, `activityModels`(数组), `acl`

**ActivityModel**：`taskModels`(数组，每项含 `role`(含 name))

**运行时 Task**：`title`, `status`(非 null), `worker`(含 login+name), `assignedUsers`(数组), `assignedGroups`(数组)

**Role**：`name`, `defaultAssignedUsers`(数组含 login+name), `defaultAssignedGroups`(数组含 id)

---

## 8. i18n Key 清单

P5 涉及的异常 i18n key（复用已有 i18n 基础设施）：

| Key | 场景 |
|-----|------|
| `AccessRightException` | ACL 写权限不足 |
| `NotAllowedException7` | 目录结构已锁定 |
| `NotAllowedException9` | 名称不合规 |
| `NotAllowedException56` | 工作流 Task 无潜在工作者 |
| `EntityConstraintException11` | 删除用户组时仍有成员 |
| `EntityConstraintException25` | 删除角色/工作流模板时正在使用 |
| `UserNotFoundException` | 用户不存在 |
| `UserGroupNotFoundException` | 用户组不存在 |
| `CreationException` | 创建失败 |
| `AccountAlreadyExistsException` | 账号已存在 |

Auth 补全新增：
- 密码恢复邮件相关 key（需查 `LocalStrings.properties`）

---

## 9. 执行顺序

1. **ORM 建模** — 4 个模型文件（user_mgmt / security / workflow / notification）
2. **ACL/Role** — security_service + acl_helper + roles.py 路由 + 给已有路由补 ACL 端点
3. **用户/账号/组管理** — user_mgmt_service + users.py + accounts.py
4. **工作流** — workflow_service + workflows.py
5. **通知** — notification_service + notifications.py
6. **Webhook** — webhooks.py
7. **Auth 补全** — auth.py 修改
8. **对齐审计** — 逐方法对照 Payara 校验点 / i18n key / DTO 字段
9. **Payara 对拍** — compare_with_payara.py
10. **前端实测清单**
11. **切 Nginx 路由**
12. **更新文档** — CHANGELOG + REMINDERS + 路线图

---

## 10. 对齐债务清偿

P5 落地后补齐的最后一条对齐债务：
- **PartRevisionDTO.notifications 字段** — 从 `modificationnotification` 表查询并填充

---

## 11. 已知风险

1. **Activity 单表继承** — SQLAlchemy `polymorphic_on=dtype` 需要正确配置，否则 ORM 查询返回基类
2. **process_task 状态机** — MVP 只记录状态不自动推进，前端有手动 relaunch 但用户体验不完整
3. **OAuth provider 配置** — 需查证 DB 表或配置文件中是否有 OAuth provider 数据
4. **Nginx 路由冲突** — `/workspaces/{ws}/users` 和散落的 `add-user` 等端点需要精心排序正则
5. **ACL 散落端点** — 给已有路由补 ACL 端点时需修改 parts.py/documents.py/products.py，注意不破坏现有功能
6. **SMTP 密码恢复** — MailHog 容器已在 8003 端口运行，但 FastAPI 需要新增 SMTP 客户端代码
7. **role_usergroupmapping 表不存在** — 实际表名是 `role_user` 和 `role_usergroup`（已确认）
8. **前端运行时对象** — Workflow/Task/Activity 在前端不是 Backbone Model，是纯 JS 对象，无 parse() 保护，字段缺失直接 TypeError

---

## 12. 测试策略

- **ORM 模型测试**：表名验证 + 关系验证
- **Service 单元测试**：CRUD + 权限检查 + 异常路径
- **API 集成测试**：创建→列表→编辑→删除 全流程
- **ACL 测试**：设置 ACL → 非授权用户 403 → 授权用户 200
- **对拍**：compare_with_payara.py 逐端点对比
- **前端实测清单**：用户管理页面 / 角色管理页面 / 工作流模板编辑器 / 通知列表
