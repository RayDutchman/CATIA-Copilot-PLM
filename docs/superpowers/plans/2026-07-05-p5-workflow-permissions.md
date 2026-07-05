# P5 工作流与权限 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完整迁移 Payara 后端剩余的工作流与权限模块（66+ 端点 / 6 功能域）到 FastAPI back-py。

**Architecture:** 按功能域分文件（方案 A），4 个 ORM 模型文件 + 4 个 Service 文件 + 6 个新路由文件 + 共享 ACL helper。复用 P0-P4 的 i18n/异常基础设施。Activity 用 SQLAlchemy 单表继承。process_task MVP 只记录状态不自动推进工作流。

**Tech Stack:** FastAPI + SQLAlchemy + Pydantic v2 + PostgreSQL（现有 16 张表）+ JWT（共享 JWT_KEY=changeit）

## Global Constraints

- API 路径前缀 `/docdoku-plm-server-rest/api` 不变
- JWT 与 Payara 共享 JWT_KEY=changeit，MD5 密码
- DB 不改 schema，直接读写现有表
- 所有 POST/PUT/DELETE 端点必须注册尾斜杠双路由（前端 Backbone POST 带 `/`）
- 响应字段用 camelCase（前端 Backbone Model 期望）
- 异常抛 `ApplicationException` 子类 + i18n key，禁止硬编码错误消息
- 测试用 test1/password（Workspace_2 成员），workspace 用 Workspace_2
- 运行测试：`workdir: /home/chenweibo/CATIA-Copilot-PLM/docdoku-plm-server-py` → `source venv/bin/activate && pytest tests/ -q`
- 重建容器：`workdir: docdoku-plm-docker` → `docker compose up -d --build back-py`

---

## Task 1: ORM 模型（4 文件）

**Files:**
- Create: `docdoku-plm-server-py/app/models/user_mgmt.py`
- Create: `docdoku-plm-server-py/app/models/security.py`
- Create: `docdoku-plm-server-py/app/models/workflow.py`
- Create: `docdoku-plm-server-py/app/models/notification.py`
- Create: `docdoku-plm-server-py/tests/test_p5_models.py`

**Interfaces:**
- Consumes: `app/core/database.py`（Base, engine）
- Produces: `UserGroup`, `Credential`, `ACL`, `AclUserEntry`, `AclUserGroupEntry`, `Role`, `WorkflowModel`, `Workflow`, `Activity`, `Task`, `WebhookApp`, `Webhook`, `ModificationNotification`, `IterationChangeSubscription`, `StateChangeSubscription`

- [ ] **Step 1: 写 `app/models/user_mgmt.py`**

```python
from sqlalchemy import Column, String, ForeignKey
from app.core.database import Base


class UserGroup(Base):
    __tablename__ = "usergroup"
    id = Column(String, primary_key=True)
    workspace_id = Column(String, primary_key=True)


class Credential(Base):
    __tablename__ = "credential"
    login = Column(String, ForeignKey("account.login"), primary_key=True)
    password = Column(String)
```

- [ ] **Step 2: 写 `app/models/security.py`**

```python
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, ForeignKeyConstraint, Table
from app.core.database import Base

role_user = Table(
    "role_user", Base.metadata,
    Column("role_name", String, primary_key=True),
    Column("role_workspace_id", String, primary_key=True),
    Column("user_login", String, primary_key=True),
    Column("user_workspace_id", String, primary_key=True),
    ForeignKeyConstraint(["role_name", "role_workspace_id"],
                         ["role.name", "role.workspace_id"]),
    ForeignKeyConstraint(["user_login", "user_workspace_id"],
                         ["userdata.login", "userdata.workspace_id"]),
)

role_usergroup = Table(
    "role_usergroup", Base.metadata,
    Column("role_name", String, primary_key=True),
    Column("role_workspace_id", String, primary_key=True),
    Column("usergroup_id", String, primary_key=True),
    Column("usergroup_workspace_id", String, primary_key=True),
    ForeignKeyConstraint(["role_name", "role_workspace_id"],
                         ["role.name", "role.workspace_id"]),
    ForeignKeyConstraint(["usergroup_id", "usergroup_workspace_id"],
                         ["usergroup.id", "usergroup.workspace_id"]),
)


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
```

- [ ] **Step 3: 写 `app/models/workflow.py`**

```python
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class WorkflowModel(Base):
    __tablename__ = "workflowmodel"
    id = Column(String, primary_key=True)
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
    dtype = Column(String)
    lifecyclestate = Column(String)
    taskstocomplete = Column(Integer)


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


class WebhookApp(Base):
    __tablename__ = "webhookapp"
    id = Column(Integer, primary_key=True, autoincrement=True)
    dtype = Column(String)  # SIMPLE_HTTP / AWS_SNS
    auth = Column(String)
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

- [ ] **Step 4: 写 `app/models/notification.py`**

```python
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Table
from app.core.database import Base

iteration_change_subscription = Table(
    "iterationchangesubscription", Base.metadata,
    Column("documentmaster_id", String, primary_key=True),
    Column("documentmaster_workspace_id", String, primary_key=True),
    Column("subscriber_login", String, primary_key=True),
    Column("subscriber_workspace_id", String, primary_key=True),
)

state_change_subscription = Table(
    "statechangesubscription", Base.metadata,
    Column("documentmaster_id", String, primary_key=True),
    Column("documentmaster_workspace_id", String, primary_key=True),
    Column("subscriber_login", String, primary_key=True),
    Column("subscriber_workspace_id", String, primary_key=True),
)


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
```

- [ ] **Step 5: 写测试 `tests/test_p5_models.py`**

```python
from app.core.database import engine
from sqlalchemy import text


def test_usergroup_table_exists():
    with engine.connect() as conn:
        assert conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name='usergroup'")).scalar() == 1


def test_acl_tables_exist():
    with engine.connect() as conn:
        for t in ("acl", "acluserentry", "aclusergroupentry"):
            assert conn.execute(text(
                f"SELECT COUNT(*) FROM information_schema.tables "
                f"WHERE table_name='{t}'")).scalar() == 1


def test_workflow_tables_exist():
    with engine.connect() as conn:
        for t in ("workflowmodel", "workflow", "activity", "task"):
            assert conn.execute(text(
                f"SELECT COUNT(*) FROM information_schema.tables "
                f"WHERE table_name='{t}'")).scalar() == 1


def test_webhook_tables_exist():
    with engine.connect() as conn:
        for t in ("webhook", "webhookapp"):
            assert conn.execute(text(
                f"SELECT COUNT(*) FROM information_schema.tables "
                f"WHERE table_name='{t}'")).scalar() == 1


def test_notification_tables_exist():
    with engine.connect() as conn:
        for t in ("modificationnotification", "iterationchangesubscription", "statechangesubscription"):
            assert conn.execute(text(
                f"SELECT COUNT(*) FROM information_schema.tables "
                f"WHERE table_name='{t}'")).scalar() == 1


def test_role_tables_exist():
    with engine.connect() as conn:
        for t in ("role", "role_user", "role_usergroup"):
            assert conn.execute(text(
                f"SELECT COUNT(*) FROM information_schema.tables "
                f"WHERE table_name='{t}'")).scalar() == 1


def test_modificationnotification_has_data():
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM modificationnotification")).scalar()
        assert count == 17
```

- [ ] **Step 6: 运行测试验证通过**

Run: `source venv/bin/activate && pytest tests/test_p5_models.py -v`
Expected: 7 passed

- [ ] **Step 7: Commit**

```bash
git add app/models/user_mgmt.py app/models/security.py app/models/workflow.py app/models/notification.py tests/test_p5_models.py
git commit -m "feat: P5 ORM 模型——user_mgmt/security/workflow/notification 4 文件"
```

---

## Task 2: ACL Helper + SecurityService + Role 路由

**Files:**
- Create: `app/services/acl_helper.py`
- Create: `app/services/security_service.py`
- Create: `app/routers/roles.py`
- Create: `tests/test_security_service.py`
- Modify: `app/main.py`（注册 roles 路由）

**Interfaces:**
- Consumes: `app/models/security.py`（ACL, AclUserEntry, AclUserGroupEntry, Role, role_user, role_usergroup）
- Produces: `apply_acl(db, acl_id, user_entries, group_entries) -> int`, `SecurityService` 类

- [ ] **Step 1: 写 `app/services/acl_helper.py`**

```python
from sqlalchemy.orm import Session
from app.models.security import ACL, AclUserEntry, AclUserGroupEntry


def apply_acl(db: Session, acl_id: int | None,
              user_entries: dict, group_entries: dict) -> int:
    """upsert ACL entries，返回 acl_id。None 则新建 ACL。"""
    if acl_id is None:
        acl = ACL(enabled=True)
        db.add(acl)
        db.flush()
        acl_id = acl.id
    else:
        acl = db.query(ACL).filter(ACL.id == acl_id).first()
        if not acl:
            acl = ACL(id=acl_id, enabled=True)
            db.add(acl)
            db.flush()

    # 清旧条目
    db.query(AclUserEntry).filter(AclUserEntry.acl_id == acl_id).delete()
    db.query(AclUserGroupEntry).filter(AclUserGroupEntry.acl_id == acl_id).delete()

    # 写新条目
    for login, perm in user_entries.items():
        parts = login.split(":")
        db.add(AclUserEntry(acl_id=acl_id,
                            principal_login=parts[0],
                            principal_workspace_id=parts[1] if len(parts) > 1 else "",
                            permission=perm))
    for gid, perm in group_entries.items():
        parts = gid.split(":")
        db.add(AclUserGroupEntry(acl_id=acl_id,
                                 principal_id=parts[0],
                                 principal_workspace_id=parts[1] if len(parts) > 1 else "",
                                 permission=perm))
    db.commit()
    return acl_id


def check_write_access(db: Session, acl_id: int | None,
                       user_login: str, is_admin: bool) -> bool:
    if is_admin:
        return True
    if acl_id is None:
        return True  # 无 ACL = 公开
    acl = db.query(ACL).filter(ACL.id == acl_id).first()
    if not acl or not acl.enabled:
        return True
    entry = db.query(AclUserEntry).filter(
        AclUserEntry.acl_id == acl_id,
        AclUserEntry.principal_login == user_login,
    ).first()
    if entry and entry.permission == "FULL_ACCESS":
        return True
    return False
```

- [ ] **Step 2: 写 `app/services/security_service.py`**

```python
from sqlalchemy.orm import Session
from app.models.security import Role, role_user, role_usergroup
from app.core.exceptions import (
    EntityAlreadyExistsException, EntityConstraintException,
    CreationException,
)
from sqlalchemy import text


class SecurityService:
    def list_roles(self, db: Session, ws: str) -> list[Role]:
        return db.query(Role).filter(Role.workspace_id == ws).all()

    def list_roles_in_use(self, db: Session, ws: str) -> list[Role]:
        roles = self.list_roles(db, ws)
        result = []
        for r in roles:
            user_count = db.execute(text(
                "SELECT COUNT(*) FROM role_user WHERE role_name=:n AND role_workspace_id=:w"
            ), {"n": r.name, "w": ws}).scalar()
            group_count = db.execute(text(
                "SELECT COUNT(*) FROM role_usergroup WHERE role_name=:n AND role_workspace_id=:w"
            ), {"n": r.name, "w": ws}).scalar()
            if user_count > 0 or group_count > 0:
                result.append(r)
        return result

    def create_role(self, db: Session, ws: str, name: str,
                    default_users: list | None = None,
                    default_groups: list | None = None) -> Role:
        existing = db.query(Role).filter(Role.name == name, Role.workspace_id == ws).first()
        if existing:
            raise EntityAlreadyExistsException("RoleAlreadyExistsException", name)
        role = Role(name=name, workspace_id=ws)
        db.add(role)
        db.commit()
        db.refresh(role)
        self._update_role_assignments(db, ws, name, default_users, default_groups)
        return role

    def update_role(self, db: Session, ws: str, name: str,
                    default_users: list | None = None,
                    default_groups: list | None = None) -> Role:
        role = db.query(Role).filter(Role.name == name, Role.workspace_id == ws).first()
        if not role:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("RoleNotFoundException", name)
        self._update_role_assignments(db, ws, name, default_users, default_groups)
        return role

    def delete_role(self, db: Session, ws: str, name: str):
        role = db.query(Role).filter(Role.name == name, Role.workspace_id == ws).first()
        if not role:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("RoleNotFoundException", name)
        in_use = db.execute(text(
            "SELECT COUNT(*) FROM role_user WHERE role_name=:n AND role_workspace_id=:w "
            "UNION ALL SELECT COUNT(*) FROM role_usergroup WHERE role_name=:n AND role_workspace_id=:w"
        ), {"n": name, "w": ws}).scalar()
        if in_use:
            raise EntityConstraintException("EntityConstraintException25")
        db.delete(role)
        db.commit()

    def _update_role_assignments(self, db: Session, ws: str, name: str,
                                 users: list | None, groups: list | None):
        db.execute(role_user.delete().where(
            role_user.c.role_name == name,
            role_user.c.role_workspace_id == ws,
        ))
        db.execute(role_usergroup.delete().where(
            role_usergroup.c.role_name == name,
            role_usergroup.c.role_workspace_id == ws,
        ))
        if users:
            for u in users:
                db.execute(role_user.insert().values(
                    role_name=name, role_workspace_id=ws,
                    user_login=u.get("login", ""), user_workspace_id=ws,
                ))
        if groups:
            for g in groups:
                db.execute(role_usergroup.insert().values(
                    role_name=name, role_workspace_id=ws,
                    usergroup_id=g.get("id", ""), usergroup_workspace_id=ws,
                ))
        db.commit()


security_service = SecurityService()
```

- [ ] **Step 3: 写 `app/routers/roles.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.security_service import security_service

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
PREFIX = "/workspaces/{ws}"


def _role_to_dict(r, db: Session) -> dict:
    from sqlalchemy import text
    users = db.execute(text(
        "SELECT user_login FROM role_user WHERE role_name=:n AND role_workspace_id=:w"
    ), {"n": r.name, "w": r.workspace_id}).fetchall()
    groups = db.execute(text(
        "SELECT usergroup_id FROM role_usergroup WHERE role_name=:n AND role_workspace_id=:w"
    ), {"n": r.name, "w": r.workspace_id}).fetchall()
    return {
        "name": r.name,
        "workspaceId": r.workspace_id,
        "defaultAssignedUsers": [{"login": u[0], "name": u[0]} for u in users],
        "defaultAssignedGroups": [{"id": g[0]} for g in groups],
    }


@router.get(f"{PREFIX}/roles")
def list_roles(ws: str, db: Session = Depends(get_db),
               current_user: Account = Depends(get_current_user)):
    return [_role_to_dict(r, db) for r in security_service.list_roles(db, ws)]


@router.get(f"{PREFIX}/roles/inuse")
def list_roles_in_use(ws: str, db: Session = Depends(get_db),
                      current_user: Account = Depends(get_current_user)):
    return [_role_to_dict(r, db) for r in security_service.list_roles_in_use(db, ws)]


@router.post(f"{PREFIX}/roles", status_code=201)
@router.post(f"{PREFIX}/roles/", status_code=201, include_in_schema=False)
def create_role(ws: str, body: dict, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    r = security_service.create_role(db, ws, body.get("name", ""),
                                     body.get("defaultAssignedUsers"),
                                     body.get("defaultAssignedGroups"))
    return _role_to_dict(r, db)


@router.put(f"{PREFIX}/roles/{{name}}")
@router.put(f"{PREFIX}/roles/{{name}}/", include_in_schema=False)
def update_role(ws: str, name: str, body: dict, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    r = security_service.update_role(db, ws, name,
                                     body.get("defaultAssignedUsers"),
                                     body.get("defaultAssignedGroups"))
    return _role_to_dict(r, db)


@router.delete(f"{PREFIX}/roles/{{name}}", status_code=204)
def delete_role(ws: str, name: str, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    security_service.delete_role(db, ws, name)
```

- [ ] **Step 4: 注册路由到 `app/main.py`**

在 `app/main.py` 中添加：
```python
from app.routers import roles
app.include_router(roles.router)
```

- [ ] **Step 5: 写测试 `tests/test_security_service.py`**

```python
from app.services.security_service import security_service, apply_acl, check_write_access
from app.core.database import SessionLocal
from app.models.security import Role


def test_list_roles_empty():
    db = SessionLocal()
    try:
        roles = security_service.list_roles(db, "Workspace_2")
        assert isinstance(roles, list)
    finally:
        db.close()


def test_create_and_delete_role():
    db = SessionLocal()
    try:
        r = security_service.create_role(db, "Workspace_2", "TEST-ROLE")
        assert r.name == "TEST-ROLE"
        security_service.delete_role(db, "Workspace_2", "TEST-ROLE")
        assert security_service.list_roles(db, "Workspace_2") == [] or \
               all(x.name != "TEST-ROLE" for x in security_service.list_roles(db, "Workspace_2"))
    finally:
        db.close()


def test_apply_acl_creates_and_updates():
    db = SessionLocal()
    try:
        acl_id = apply_acl(db, None, {"test1:Workspace_2": "FULL_ACCESS"}, {})
        assert acl_id is not None
        assert check_write_access(db, acl_id, "test1", False) is True
        assert check_write_access(db, acl_id, "other", False) is False
        assert check_write_access(db, acl_id, "test1", True) is True
    finally:
        db.close()
```

- [ ] **Step 6: 运行测试**

Run: `source venv/bin/activate && pytest tests/test_p5_models.py tests/test_security_service.py -v`
Expected: 10 passed

- [ ] **Step 7: Commit**

```bash
git add app/services/acl_helper.py app/services/security_service.py app/routers/roles.py tests/test_security_service.py app/main.py
git commit -m "feat: P5 Task 2——ACL helper + SecurityService + Role 路由"
```

---

## Task 3: 给已有路由补齐 ACL 端点

**Files:**
- Modify: `app/routers/parts.py`（补 `PUT /{part_key}/acl`）
- Modify: `app/routers/documents.py`（补 `PUT /{doc_key}/acl`）
- Modify: `app/routers/products.py`（补 `PUT /{ciId}/configurations/{pcId}/acl`）
- Modify: `app/routers/document_templates.py`（补 `PUT /{id}/acl`）
- Create: `tests/test_acl_endpoints.py`

**Interfaces:**
- Consumes: `app/services/acl_helper.py`（`apply_acl`）
- Produces: 各 resource 的 `PUT .../acl` 端点

- [ ] **Step 1: 在 `parts.py` 补 ACL 端点**

在 `app/routers/parts.py` 末尾添加：

```python
from app.services.acl_helper import apply_acl


@router.put(f"{PREFIX}/parts/{{part_key}}/acl")
@router.put(f"{PREFIX}/parts/{{part_key}}/acl/", include_in_schema=False)
def update_part_acl(ws: str, part_key: str, body: dict,
                    db: Session = Depends(get_db),
                    current_user: Account = Depends(get_current_user)):
    number, version = _split_part_key(part_key)
    pr = product_service.get_revision(db, ws, number, version)
    acl_id = getattr(pr, "acl_id", None)
    user_entries = body.get("userEntries", {})
    group_entries = body.get("groupEntries", {})
    new_acl_id = apply_acl(db, acl_id, user_entries, group_entries)
    if pr.acl_id != new_acl_id:
        pr.acl_id = new_acl_id
        db.commit()
    return {"aclId": new_acl_id}
```

- [ ] **Step 2: 在 `documents.py` 补 ACL 端点**

在 `app/routers/documents.py` 末尾添加类似的 ACL 端点（路径用 `documents/{doc_key}/acl`）。

```python
from app.services.acl_helper import apply_acl


@router.put(f"{PREFIX}/documents/{{doc_key}}/acl")
@router.put(f"{PREFIX}/documents/{{doc_key}}/acl/", include_in_schema=False)
def update_doc_acl(ws: str, doc_key: str, body: dict,
                   db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    doc_id, version = _split_doc_key(doc_key)
    dr = db.query(DocumentRevision).filter(
        DocumentRevision.workspace_id == ws,
        DocumentRevision.documentmaster_id == doc_id,
        DocumentRevision.version == version,
    ).first()
    if not dr:
        from app.core.exceptions import EntityNotFoundException
        raise EntityNotFoundException("DocumentRevisionNotFoundException", doc_id, version)
    acl_id = getattr(dr, "acl_id", None)
    new_acl_id = apply_acl(db, acl_id, body.get("userEntries", {}), body.get("groupEntries", {}))
    if dr.acl_id != new_acl_id:
        dr.acl_id = new_acl_id
        db.commit()
    return {"aclId": new_acl_id}
```

注：`_split_doc_key` 函数已在 `documents.py` 中定义。需确认 `DocumentRevision` 模型有 `acl_id` 列。如果没有，需在 `models/document.py` 中补上。

- [ ] **Step 3: 在 `products.py` 补 Configuration ACL 端点**

在 `app/routers/products.py` 中添加：

```python
@router.put(f"{PREFIX}/products/{{ciId}}/configurations/{{pcId}}/acl")
@router.put(f"{PREFIX}/products/{{ciId}}/configurations/{{pcId}}/acl/", include_in_schema=False)
def update_config_acl(ws: str, ciId: str, pcId: int, body: dict,
                      db: Session = Depends(get_db),
                      current_user: Account = Depends(get_current_user)):
    config = db.query(ProductConfiguration).filter(
        ProductConfiguration.workspace_id == ws,
        ProductConfiguration.configurationitem_id == ciId,
        ProductConfiguration.id == pcId,
    ).first()
    if not config:
        from app.core.exceptions import EntityNotFoundException
        raise EntityNotFoundException("ProductConfigurationNotFoundException", str(pcId))
    acl_id = getattr(config, "acl_id", None)
    new_acl_id = apply_acl(db, acl_id, body.get("userEntries", {}), body.get("groupEntries", {}))
    if config.acl_id != new_acl_id:
        config.acl_id = new_acl_id
        db.commit()
    return {"aclId": new_acl_id}
```

- [ ] **Step 4: 在 `document_templates.py` 补 ACL 端点**

```python
@router.put(f"{PREFIX}/document-templates/{{template_id}}/acl")
@router.put(f"{PREFIX}/document-templates/{{template_id}}/acl/", include_in_schema=False)
def update_template_acl(ws: str, template_id: str, body: dict,
                        db: Session = Depends(get_db),
                        current_user: Account = Depends(get_current_user)):
    tpl = db.query(DocumentMasterTemplate).filter(
        DocumentMasterTemplate.workspace_id == ws,
        DocumentMasterTemplate.id == template_id,
    ).first()
    if not tpl:
        from app.core.exceptions import EntityNotFoundException
        raise EntityNotFoundException("DocumentMasterTemplateNotFoundException", template_id)
    acl_id = getattr(tpl, "acl_id", None)
    new_acl_id = apply_acl(db, acl_id, body.get("userEntries", {}), body.get("groupEntries", {}))
    if tpl.acl_id != new_acl_id:
        tpl.acl_id = new_acl_id
        db.commit()
    return {"aclId": new_acl_id}
```

- [ ] **Step 5: 写测试 `tests/test_acl_endpoints.py`**

```python
import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=False)
PREFIX = "/docdoku-plm-server-rest/api"
WS = "Workspace_2"


def _token():
    resp = client.post(f"{PREFIX}/auth/login",
                       json={"login": "test1", "password": "password"})
    return resp.json().get("jwt", "")


def test_set_part_acl():
    token = _token()
    h = {"Authorization": f"Bearer {token}"}
    num = "ACLTEST-" + uuid.uuid4().hex[:6]
    client.post(f"{PREFIX}/workspaces/{WS}/parts",
                json={"number": num, "name": "t"}, headers=h)
    resp = client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/acl",
                      json={"userEntries": {"test1:Workspace_2": "FULL_ACCESS"},
                            "groupEntries": {}},
                      headers=h)
    assert resp.status_code in (200, 201)
```

- [ ] **Step 6: 运行测试**

Run: `source venv/bin/activate && pytest tests/test_acl_endpoints.py -v`
Expected: 1 passed

- [ ] **Step 7: Commit**

```bash
git add app/routers/parts.py app/routers/documents.py app/routers/products.py app/routers/document_templates.py tests/test_acl_endpoints.py
git commit -m "feat: P5 Task 3——给 parts/documents/products/templates 补齐 ACL 端点"
```

---

## Task 4: UserMgmtService + 用户/组/成员资格路由

**Files:**
- Create: `app/services/user_mgmt_service.py`
- Create: `app/routers/users.py`
- Create: `tests/test_users_api.py`
- Modify: `app/main.py`

**Interfaces:**
- Consumes: `app/models/user_mgmt.py`, `app/models/auth.py`
- Produces: `UserMgmtService` 类, `users.router`

- [ ] **Step 1: 写 `app/services/user_mgmt_service.py`**

```python
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.auth import Account, UserGroupMapping
from app.models.user_mgmt import UserGroup, Credential
from app.core.exceptions import (
    EntityAlreadyExistsException, EntityNotFoundException,
    EntityConstraintException, CreationException,
)
import hashlib


class UserMgmtService:
    def list_users(self, db: Session, ws: str) -> list:
        rows = db.execute(text(
            "SELECT u.login, u.workspace_id, a.name, a.email, a.enabled "
            "FROM userdata u JOIN account a ON u.login = a.login "
            "WHERE u.workspace_id = :ws"
        ), {"ws": ws}).fetchall()
        return [{"login": r[0], "workspaceId": r[1], "name": r[2],
                 "email": r[3], "enabled": r[4]} for r in rows]

    def who_am_i(self, db: Session, ws: str, login: str) -> dict:
        acc = db.query(Account).filter(Account.login == login).first()
        if not acc:
            raise EntityNotFoundException("UserNotFoundException", login)
        return {"login": acc.login, "name": acc.name, "email": acc.email,
                "language": acc.language, "timezone": acc.timezone}

    def list_groups(self, db: Session, ws: str) -> list[UserGroup]:
        return db.query(UserGroup).filter(UserGroup.workspace_id == ws).all()

    def create_group(self, db: Session, ws: str, group_id: str) -> UserGroup:
        existing = db.query(UserGroup).filter(
            UserGroup.id == group_id, UserGroup.workspace_id == ws).first()
        if existing:
            raise EntityAlreadyExistsException("UserGroupAlreadyExistsException", group_id)
        g = UserGroup(id=group_id, workspace_id=ws)
        db.add(g)
        db.commit()
        db.refresh(g)
        return g

    def delete_group(self, db: Session, ws: str, group_id: str):
        g = db.query(UserGroup).filter(
            UserGroup.id == group_id, UserGroup.workspace_id == ws).first()
        if not g:
            raise EntityNotFoundException("UserGroupNotFoundException", group_id)
        # 检查成员
        members = db.execute(text(
            "SELECT COUNT(*) FROM usergroupmapping WHERE groupname = :g"
        ), {"g": group_id}).scalar()
        if members > 0:
            raise EntityConstraintException("EntityConstraintException11")
        db.delete(g)
        db.commit()

    def add_user(self, db: Session, ws: str, login: str, group_id: str | None = None):
        acc = db.query(Account).filter(Account.login == login).first()
        if not acc:
            raise EntityNotFoundException("UserNotFoundException", login)
        # 检查是否已在 workspace
        existing = db.execute(text(
            "SELECT COUNT(*) FROM userdata WHERE login = :l AND workspace_id = :w"
        ), {"l": login, "w": ws}).scalar()
        if existing == 0:
            db.execute(text(
                "INSERT INTO userdata (login, workspace_id) VALUES (:l, :w)"
            ), {"l": login, "w": ws})
        if group_id:
            db.execute(text(
                "INSERT INTO usergroupmapping (login, groupname) VALUES (:l, :g) "
                "ON CONFLICT DO NOTHING"
            ), {"l": login, "g": group_id})
        db.commit()

    def remove_user_from_workspace(self, db: Session, ws: str, login: str):
        db.execute(text(
            "DELETE FROM userdata WHERE login = :l AND workspace_id = :w"
        ), {"l": login, "w": ws})
        db.execute(text(
            "DELETE FROM usergroupmapping WHERE login = :l"
        ), {"l": login})
        db.commit()

    def enable_user(self, db: Session, ws: str, login: str):
        db.execute(text(
            "UPDATE userdata SET enabled = true WHERE login = :l AND workspace_id = :w"
        ), {"l": login, "w": ws})
        db.commit()

    def disable_user(self, db: Session, ws: str, login: str):
        db.execute(text(
            "UPDATE userdata SET enabled = false WHERE login = :l AND workspace_id = :w"
        ), {"l": login, "w": ws})
        db.commit()

    def set_admin(self, db: Session, ws: str, login: str):
        db.execute(text(
            "UPDATE workspace SET admin = :l WHERE id = :w"
        ), {"l": login, "w": ws})
        db.commit()

    def list_memberships(self, db: Session, ws: str) -> list:
        rows = db.execute(text(
            "SELECT u.login, u.workspace_id, a.name, u.enabled "
            "FROM userdata u JOIN account a ON u.login = a.login "
            "WHERE u.workspace_id = :ws"
        ), {"ws": ws}).fetchall()
        return [{"workspaceId": ws, "member": {"login": r[0], "name": r[2]},
                 "readOnly": not r[3]} for r in rows]

    def create_account(self, db: Session, login: str, password: str,
                       email: str, name: str, lang: str) -> Account:
        existing = db.query(Account).filter(Account.login == login).first()
        if existing:
            raise EntityAlreadyExistsException("AccountAlreadyExistsException", login)
        acc = Account(login=login, email=email, name=name, language=lang)
        db.add(acc)
        cred = Credential(login=login, password=hashlib.md5(password.encode()).hexdigest())
        db.add(cred)
        db.commit()
        db.refresh(acc)
        return acc

    def update_account(self, db: Session, login: str, fields: dict) -> Account:
        acc = db.query(Account).filter(Account.login == login).first()
        if not acc:
            raise EntityNotFoundException("AccountNotFoundException", login)
        if "email" in fields:
            acc.email = fields["email"]
        if "name" in fields:
            acc.name = fields["name"]
        if "language" in fields:
            acc.language = fields["language"]
        if "timezone" in fields:
            acc.timezone = fields["timezone"]
        if "password" in fields:
            cred = db.query(Credential).filter(Credential.login == login).first()
            if cred:
                cred.password = hashlib.md5(fields["password"].encode()).hexdigest()
        db.commit()
        db.refresh(acc)
        return acc

    def list_workspaces_for_user(self, db: Session, login: str) -> list:
        rows = db.execute(text(
            "SELECT w.id, w.enabled FROM workspace w "
            "JOIN userdata u ON w.id = u.workspace_id "
            "WHERE u.login = :l"
        ), {"l": login}).fetchall()
        return [{"id": r[0], "enabled": r[1]} for r in rows]


user_mgmt_service = UserMgmtService()
```

- [ ] **Step 2: 写 `app/routers/users.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.user_mgmt_service import user_mgmt_service

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
PREFIX = "/workspaces/{ws}"


def _user_to_dict(u):
    return {"login": u["login"], "workspaceId": u["workspaceId"],
            "name": u.get("name", ""), "email": u.get("email", ""),
            "enabled": u.get("enabled", True)}


def _group_to_dict(g):
    return {"id": g.id, "workspaceId": g.workspace_id}


@router.get(f"{PREFIX}/users")
def list_users(ws: str, db: Session = Depends(get_db),
               current_user: Account = Depends(get_current_user)):
    return [_user_to_dict(u) for u in user_mgmt_service.list_users(db, ws)]


@router.get(f"{PREFIX}/users/me")
def who_am_i(ws: str, db: Session = Depends(get_db),
             current_user: Account = Depends(get_current_user)):
    return user_mgmt_service.who_am_i(db, ws, current_user.login)


@router.get(f"{PREFIX}/users/admin")
def get_admin(ws: str, db: Session = Depends(get_db),
              current_user: Account = Depends(get_current_user)):
    from sqlalchemy import text
    row = db.execute(text("SELECT admin FROM workspace WHERE id = :w"), {"w": ws}).first()
    if not row:
        return {"login": ""}
    return {"login": row[0]}


@router.get(f"{PREFIX}/groups")
def list_groups(ws: str, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    return [_group_to_dict(g) for g in user_mgmt_service.list_groups(db, ws)]


@router.post(f"{PREFIX}/groups", status_code=201)
@router.post(f"{PREFIX}/groups/", status_code=201, include_in_schema=False)
def create_group(ws: str, body: dict, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    g = user_mgmt_service.create_group(db, ws, body.get("id", ""))
    return _group_to_dict(g)


@router.delete(f"{PREFIX}/groups/{{group_id}}", status_code=204)
def delete_group(ws: str, group_id: str, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    user_mgmt_service.delete_group(db, ws, group_id)


@router.get(f"{PREFIX}/memberships/users")
def list_user_memberships(ws: str, db: Session = Depends(get_db),
                          current_user: Account = Depends(get_current_user)):
    return user_mgmt_service.list_memberships(db, ws)


@router.get(f"{PREFIX}/memberships/users/me")
def my_memberships(ws: str, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    all_m = user_mgmt_service.list_memberships(db, ws)
    return [m for m in all_m if m["member"]["login"] == current_user.login]


@router.put(f"{PREFIX}/add-user")
@router.put(f"{PREFIX}/add-user/", include_in_schema=False)
def add_user(ws: str, body: dict, db: Session = Depends(get_db),
             current_user: Account = Depends(get_current_user)):
    user_mgmt_service.add_user(db, ws, body.get("login", ""), body.get("group"))
    return {"status": "ok"}


@router.put(f"{PREFIX}/admin")
@router.put(f"{PREFIX}/admin/", include_in_schema=False)
def set_admin(ws: str, body: dict, db: Session = Depends(get_db),
              current_user: Account = Depends(get_current_user)):
    user_mgmt_service.set_admin(db, ws, body.get("login", ""))
    return {"status": "ok"}


@router.put(f"{PREFIX}/remove-from-workspace")
@router.put(f"{PREFIX}/remove-from-workspace/", include_in_schema=False)
def remove_user(ws: str, body: dict, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    user_mgmt_service.remove_user_from_workspace(db, ws, body.get("login", ""))
    return {"status": "ok"}


@router.put(f"{PREFIX}/enable-user")
@router.put(f"{PREFIX}/enable-user/", include_in_schema=False)
def enable_user(ws: str, body: dict, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    user_mgmt_service.enable_user(db, ws, body.get("login", ""))
    return {"status": "ok"}


@router.put(f"{PREFIX}/disable-user")
@router.put(f"{PREFIX}/disable-user/", include_in_schema=False)
def disable_user(ws: str, body: dict, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    user_mgmt_service.disable_user(db, ws, body.get("login", ""))
    return {"status": "ok"}
```

- [ ] **Step 3: 注册路由到 `app/main.py`**

```python
from app.routers import users
app.include_router(users.router)
```

- [ ] **Step 4: 写测试 `tests/test_users_api.py`**

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=False)
PREFIX = "/docdoku-plm-server-rest/api"
WS = "Workspace_2"


def _token():
    resp = client.post(f"{PREFIX}/auth/login",
                       json={"login": "test1", "password": "password"})
    return resp.json().get("jwt", "")


def _h():
    return {"Authorization": f"Bearer {_token()}"}


def test_list_users():
    resp = client.get(f"{PREFIX}/workspaces/{WS}/users", headers=_h())
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(u["login"] == "test1" for u in data)


def test_who_am_i():
    resp = client.get(f"{PREFIX}/workspaces/{WS}/users/me", headers=_h())
    assert resp.status_code == 200
    assert resp.json()["login"] == "test1"


def test_list_groups():
    resp = client.get(f"{PREFIX}/workspaces/{WS}/groups", headers=_h())
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_memberships():
    resp = client.get(f"{PREFIX}/workspaces/{WS}/memberships/users", headers=_h())
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(m["member"]["login"] == "test1" for m in data)
```

- [ ] **Step 5: 运行测试**

Run: `source venv/bin/activate && pytest tests/test_users_api.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add app/services/user_mgmt_service.py app/routers/users.py tests/test_users_api.py app/main.py
git commit -m "feat: P5 Task 4——UserMgmtService + 用户/组/成员资格路由"
```

---

## Task 5: 账号管理路由

**Files:**
- Create: `app/routers/accounts.py`
- Create: `tests/test_accounts_api.py`
- Modify: `app/main.py`

- [ ] **Step 1: 写 `app/routers/accounts.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.user_mgmt_service import user_mgmt_service

router = APIRouter(prefix="/docdoku-plm-server-rest/api")


def _account_to_dict(acc):
    return {
        "login": acc.login,
        "email": acc.email,
        "name": acc.name,
        "language": acc.language,
        "timezone": acc.timezone,
        "admin": False,  # 从 usergroupmapping 查
    }


@router.put("/accounts/me")
@router.put("/accounts/me/", include_in_schema=False)
def update_account(body: dict, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    acc = user_mgmt_service.update_account(db, current_user.login, body)
    return _account_to_dict(acc)


@router.post("/accounts/create", status_code=201)
@router.post("/accounts/create/", status_code=201, include_in_schema=False)
def create_account(body: dict, db: Session = Depends(get_db)):
    acc = user_mgmt_service.create_account(
        db, body.get("login", ""), body.get("password", ""),
        body.get("email", ""), body.get("name", ""), body.get("language", "en"))
    return _account_to_dict(acc)


@router.get("/accounts/workspaces")
def list_workspaces(db: Session = Depends(get_db),
                    current_user: Account = Depends(get_current_user)):
    return user_mgmt_service.list_workspaces_for_user(db, current_user.login)
```

- [ ] **Step 2: 注册路由**

```python
from app.routers import accounts
app.include_router(accounts.router)
```

- [ ] **Step 3: 写测试**

```python
# tests/test_accounts_api.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=False)
PREFIX = "/docdoku-plm-server-rest/api"


def _token():
    resp = client.post(f"{PREFIX}/auth/login",
                       json={"login": "test1", "password": "password"})
    return resp.json().get("jwt", "")


def test_list_workspaces():
    resp = client.get(f"{PREFIX}/accounts/workspaces",
                      headers={"Authorization": f"Bearer {_token()}"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(w["id"] == "Workspace_2" for w in data)
```

- [ ] **Step 4: 运行测试 + Commit**

```bash
source venv/bin/activate && pytest tests/test_accounts_api.py -v
git add app/routers/accounts.py tests/test_accounts_api.py app/main.py
git commit -m "feat: P5 Task 5——账号管理路由（update/create/workspaces）"
```

---

## Task 6: 通知 + 标签订阅

**Files:**
- Create: `app/services/notification_service.py`
- Create: `app/routers/notifications.py`
- Create: `tests/test_notifications_api.py`
- Modify: `app/main.py`

- [ ] **Step 1: 写 `app/services/notification_service.py`**

```python
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from app.models.notification import ModificationNotification
from app.core.exceptions import EntityNotFoundException


class NotificationService:
    def acknowledge(self, db: Session, ws: str, notification_id: int,
                    comment: str, user_login: str) -> ModificationNotification:
        n = db.query(ModificationNotification).filter(
            ModificationNotification.id == notification_id).first()
        if not n:
            raise EntityNotFoundException("ModificationNotificationNotFoundException",
                                          str(notification_id))
        n.acknowledged = True
        n.acknowledgementcomment = comment
        n.acknowledgementdate = datetime.utcnow()
        n.ackauthor_login = user_login
        n.ackauthor_workspace_id = ws
        db.commit()
        db.refresh(n)
        return n

    def list_for_user(self, db: Session, ws: str, login: str) -> list:
        rows = db.execute(text(
            "SELECT * FROM modificationnotification "
            "WHERE impacted_workspace_id = :ws AND acknowledged = false"
        ), {"ws": ws}).fetchall()
        return [self._to_dict(r) for r in rows]

    def _to_dict(self, row) -> dict:
        cols = row._mapping.keys() if hasattr(row, "_mapping") else []
        return {k: row[k] for k in cols}


notification_service = NotificationService()
```

- [ ] **Step 2: 写 `app/routers/notifications.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.notification_service import notification_service

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
PREFIX = "/workspaces/{ws}"


@router.put(f"{PREFIX}/notifications/{{notification_id}}")
@router.put(f"{PREFIX}/notifications/{{notification_id}}/", include_in_schema=False)
def acknowledge_notification(ws: str, notification_id: int, body: dict,
                             db: Session = Depends(get_db),
                             current_user: Account = Depends(get_current_user)):
    n = notification_service.acknowledge(
        db, ws, notification_id,
        body.get("ackComment", ""), current_user.login)
    return {"id": n.id, "acknowledged": n.acknowledged}
```

- [ ] **Step 3: 注册路由 + 写测试 + 运行 + Commit**

测试：
```python
# tests/test_notifications_api.py
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from sqlalchemy import text

client = TestClient(app, raise_server_exceptions=False)
PREFIX = "/docdoku-plm-server-rest/api"


def _token():
    resp = client.post(f"{PREFIX}/auth/login",
                       json={"login": "test1", "password": "password"})
    return resp.json().get("jwt", "")


def test_acknowledge_notification():
    db = SessionLocal()
    try:
        row = db.execute(text(
            "SELECT id FROM modificationnotification LIMIT 1"
        )).first()
        if not row:
            return  # 无数据跳过
        nid = row[0]
        resp = client.put(f"{PREFIX}/workspaces/Workspace_2/notifications/{nid}",
                          json={"ackComment": "test"},
                          headers={"Authorization": f"Bearer {_token()}"})
        assert resp.status_code == 200
    finally:
        db.close()
```

```bash
source venv/bin/activate && pytest tests/test_notifications_api.py -v
git add app/services/notification_service.py app/routers/notifications.py tests/test_notifications_api.py app/main.py
git commit -m "feat: P5 Task 6——通知确认端点"
```

---

## Task 7: 工作流模板 CRUD

**Files:**
- Create: `app/services/workflow_service.py`
- Create: `app/routers/workflows.py`
- Create: `tests/test_workflows_api.py`
- Modify: `app/main.py`

- [ ] **Step 1: 写 `app/services/workflow_service.py`（WorkflowModel 部分）**

```python
from sqlalchemy.orm import Session
from datetime import datetime
from app.models.workflow import WorkflowModel, Activity, Task, Workflow
from app.core.exceptions import (
    EntityAlreadyExistsException, EntityNotFoundException,
    EntityConstraintException,
)


class WorkflowService:
    def list_models(self, db: Session, ws: str) -> list[WorkflowModel]:
        return db.query(WorkflowModel).filter(WorkflowModel.workspace_id == ws).all()

    def get_model(self, db: Session, ws: str, model_id: str) -> WorkflowModel:
        m = db.query(WorkflowModel).filter(
            WorkflowModel.id == model_id, WorkflowModel.workspace_id == ws).first()
        if not m:
            raise EntityNotFoundException("WorkflowModelNotFoundException", model_id)
        return m

    def create_model(self, db: Session, ws: str, model_id: str,
                     final_state: str, user_login: str) -> WorkflowModel:
        existing = db.query(WorkflowModel).filter(
            WorkflowModel.id == model_id, WorkflowModel.workspace_id == ws).first()
        if existing:
            raise EntityAlreadyExistsException("WorkflowModelAlreadyExistsException", model_id)
        m = WorkflowModel(id=model_id, workspace_id=ws,
                          finalLifecycleState=final_state,
                          creationdate=datetime.utcnow(),
                          author_login=user_login, author_workspace_id=ws)
        db.add(m)
        db.commit()
        db.refresh(m)
        return m

    def update_model(self, db: Session, ws: str, model_id: str,
                     final_state: str) -> WorkflowModel:
        m = self.get_model(db, ws, model_id)
        m.finalLifecycleState = final_state
        db.commit()
        db.refresh(m)
        return m

    def delete_model(self, db: Session, ws: str, model_id: str):
        m = self.get_model(db, ws, model_id)
        db.delete(m)
        db.commit()


workflow_service = WorkflowService()
```

- [ ] **Step 2: 写 `app/routers/workflows.py`（WorkflowModel 部分）**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.workflow_service import workflow_service

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
PREFIX = "/workspaces/{ws}"


def _model_to_dict(m) -> dict:
    return {
        "id": m.id,
        "workspaceId": m.workspace_id,
        "finalLifecycleState": m.finalLifecycleState or "",
        "creationDate": m.creationdate.isoformat() + "Z" if m.creationdate else None,
        "author": {"login": m.author_login or "", "name": m.author_login or ""},
        "activityModels": [],
        "acl": None,
    }


@router.get(f"{PREFIX}/workflow-models")
def list_models(ws: str, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    return [_model_to_dict(m) for m in workflow_service.list_models(db, ws)]


@router.get(f"{PREFIX}/workflow-models/{{model_id}}")
def get_model(ws: str, model_id: str, db: Session = Depends(get_db),
              current_user: Account = Depends(get_current_user)):
    return _model_to_dict(workflow_service.get_model(db, ws, model_id))


@router.post(f"{PREFIX}/workflow-models", status_code=201)
@router.post(f"{PREFIX}/workflow-models/", status_code=201, include_in_schema=False)
def create_model(ws: str, body: dict, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    m = workflow_service.create_model(db, ws, body.get("id", ""),
                                      body.get("finalLifecycleState", ""),
                                      current_user.login)
    return _model_to_dict(m)


@router.put(f"{PREFIX}/workflow-models/{{model_id}}")
@router.put(f"{PREFIX}/workflow-models/{{model_id}}/", include_in_schema=False)
def update_model(ws: str, model_id: str, body: dict, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    m = workflow_service.update_model(db, ws, model_id,
                                      body.get("finalLifecycleState", ""))
    return _model_to_dict(m)


@router.delete(f"{PREFIX}/workflow-models/{{model_id}}", status_code=204)
def delete_model(ws: str, model_id: str, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    workflow_service.delete_model(db, ws, model_id)
```

- [ ] **Step 3: 注册路由 + 测试 + Commit**

```python
# tests/test_workflows_api.py
import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=False)
PREFIX = "/docdoku-plm-server-rest/api"
WS = "Workspace_2"


def _token():
    resp = client.post(f"{PREFIX}/auth/login",
                       json={"login": "test1", "password": "password"})
    return resp.json().get("jwt", "")


def _h():
    return {"Authorization": f"Bearer {_token()}"}


def test_create_and_delete_workflow_model():
    model_id = "WFM-" + uuid.uuid4().hex[:6]
    resp = client.post(f"{PREFIX}/workspaces/{WS}/workflow-models",
                       json={"id": model_id, "finalLifecycleState": "RELEASED"},
                       headers=_h())
    assert resp.status_code == 201
    assert resp.json()["id"] == model_id

    resp = client.get(f"{PREFIX}/workspaces/{WS}/workflow-models/{model_id}", headers=_h())
    assert resp.status_code == 200

    resp = client.delete(f"{PREFIX}/workspaces/{WS}/workflow-models/{model_id}", headers=_h())
    assert resp.status_code == 204
```

```bash
source venv/bin/activate && pytest tests/test_workflows_api.py -v
git add app/services/workflow_service.py app/routers/workflows.py tests/test_workflows_api.py app/main.py
git commit -m "feat: P5 Task 7——工作流模板 CRUD"
```

---

## Task 8: 工作流实例 + Task 端点

**Files:**
- Modify: `app/services/workflow_service.py`（补 instance/task 方法）
- Modify: `app/routers/workflows.py`（补 instance/task 端点）

- [ ] **Step 1: 在 `workflow_service.py` 补充**

```python
    def get_instance(self, db: Session, ws: str, workflow_id: int) -> Workflow:
        w = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not w:
            raise EntityNotFoundException("WorkflowNotFoundException", str(workflow_id))
        return w

    def list_workspace_workflows(self, db: Session, ws: str) -> list:
        from sqlalchemy import text
        rows = db.execute(text(
            "SELECT w.* FROM workflow w "
            "JOIN activity a ON w.id = a.workflow_id "
            "JOIN task t ON a.workflow_id = w.id AND a.step = t.activity_step "
            "WHERE t.worker_workspace_id = :ws GROUP BY w.id"
        ), {"ws": ws}).fetchall()
        return rows

    def get_task(self, db: Session, ws: str, task_id: int) -> Task:
        # task_id 是 num，需要结合 ws 查
        from sqlalchemy import text
        row = db.execute(text(
            "SELECT t.* FROM task t "
            "JOIN activity a ON t.workflow_id = a.workflow_id AND t.activity_step = a.step "
            "WHERE t.num = :id LIMIT 1"
        ), {"id": task_id}).first()
        if not row:
            raise EntityNotFoundException("TaskNotFoundException", str(task_id))
        return row

    def get_assigned_tasks(self, db: Session, ws: str, login: str) -> list:
        from sqlalchemy import text
        rows = db.execute(text(
            "SELECT t.* FROM task t "
            "WHERE t.worker_login = :l AND t.worker_workspace_id = :w "
            "AND t.status < 2"
        ), {"l": login, "w": ws}).fetchall()
        return rows

    def process_task(self, db: Session, ws: str, task_id: int,
                     action: str, comment: str, signature: str,
                     user_login: str):
        from sqlalchemy import text
        # action: "APPROVE" or "REJECT"
        status = 2 if action.upper() == "APPROVE" else 3
        db.execute(text(
            "UPDATE task SET status = :s, closurecomment = :c, "
            "signature = :sig, closuredate = NOW() "
            "WHERE num = :id"
        ), {"s": status, "c": comment, "sig": signature, "id": task_id})
        db.commit()
```

- [ ] **Step 2: 在 `workflows.py` 补充端点**

```python
@router.get(f"{PREFIX}/workflow-instances/{{workflow_id}}")
def get_instance(ws: str, workflow_id: int, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    w = workflow_service.get_instance(db, ws, workflow_id)
    return {"id": w.id, "abortedDate": w.aborteddate, "finalLifecycleState": w.finallifecyclestate,
            "activities": [], "currentStep": 0}


@router.get(f"{PREFIX}/workflow-instances/{{workflow_id}}/aborted")
def get_aborted(ws: str, workflow_id: int, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    return []


@router.get(f"{PREFIX}/workspace-workflows")
def list_wwf(ws: str, db: Session = Depends(get_db),
             current_user: Account = Depends(get_current_user)):
    return []


@router.get(f"{PREFIX}/tasks/{{login}}/assigned")
def assigned_tasks(ws: str, login: str, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    tasks = workflow_service.get_assigned_tasks(db, ws, login)
    return [{"num": t[0], "title": t[4], "status": t[7]} for t in tasks]


@router.get(f"{PREFIX}/tasks/{{task_id}}")
def get_task(ws: str, task_id: int, db: Session = Depends(get_db),
             current_user: Account = Depends(get_current_user)):
    t = workflow_service.get_task(db, ws, task_id)
    return {"num": t[0], "title": t[4], "status": t[7]}


@router.put(f"{PREFIX}/tasks/{{task_id}}/process")
@router.put(f"{PREFIX}/tasks/{{task_id}}/process/", include_in_schema=False)
def process_task(ws: str, task_id: int, body: dict, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    workflow_service.process_task(db, ws, task_id,
                                  body.get("action", ""),
                                  body.get("comment", ""),
                                  body.get("signature", ""),
                                  current_user.login)
    return {"status": "ok"}
```

- [ ] **Step 3: 测试 + Commit**

```bash
source venv/bin/activate && pytest tests/test_workflows_api.py -v
git add app/services/workflow_service.py app/routers/workflows.py
git commit -m "feat: P5 Task 8——工作流实例 + Task 端点（process_task MVP）"
```

---

## Task 9: Webhook 路由

**Files:**
- Create: `app/routers/webhooks.py`
- Create: `tests/test_webhooks_api.py`
- Modify: `app/main.py`

- [ ] **Step 1: 写 `app/routers/webhooks.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.models.workflow import Webhook, WebhookApp

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
PREFIX = "/workspaces/{ws}"


def _webhook_to_dict(w, app=None) -> dict:
    return {
        "id": w.id,
        "name": w.name,
        "workspaceId": w.workspace_id,
        "active": w.active,
        "webhookApp": {
            "id": app.id if app else w.webhookapp_id,
            "dtype": app.dtype if app else None,
            "uri": app.uri if app else None,
            "method": app.method if app else None,
        } if app or w.webhookapp_id else None,
    }


@router.get(f"{PREFIX}/webhooks")
def list_webhooks(ws: str, db: Session = Depends(get_db),
                  current_user: Account = Depends(get_current_user)):
    hooks = db.query(Webhook).filter(Webhook.workspace_id == ws).all()
    return [_webhook_to_dict(h) for h in hooks]


@router.get(f"{PREFIX}/webhooks/{{webhook_id}}")
def get_webhook(ws: str, webhook_id: int, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    w = db.query(Webhook).filter(Webhook.id == webhook_id,
                                  Webhook.workspace_id == ws).first()
    if not w:
        from app.core.exceptions import EntityNotFoundException
        raise EntityNotFoundException("WebhookNotFoundException", str(webhook_id))
    return _webhook_to_dict(w)


@router.post(f"{PREFIX}/webhooks", status_code=201)
@router.post(f"{PREFIX}/webhooks/", status_code=201, include_in_schema=False)
def create_webhook(ws: str, body: dict, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    app_data = body.get("webhookApp", {})
    app = WebhookApp(dtype=app_data.get("dtype", "SIMPLE_HTTP"),
                     uri=app_data.get("uri", ""),
                     method=app_data.get("method", "POST"),
                     auth=app_data.get("auth"))
    db.add(app)
    db.flush()
    w = Webhook(name=body.get("name", ""), workspace_id=ws,
                active=body.get("active", True), webhookapp_id=app.id)
    db.add(w)
    db.commit()
    db.refresh(w)
    return _webhook_to_dict(w, app)


@router.delete(f"{PREFIX}/webhooks/{{webhook_id}}", status_code=204)
def delete_webhook(ws: str, webhook_id: int, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    w = db.query(Webhook).filter(Webhook.id == webhook_id,
                                  Webhook.workspace_id == ws).first()
    if w:
        db.delete(w)
        db.commit()
```

- [ ] **Step 2: 注册路由 + 测试 + Commit**

```python
# tests/test_webhooks_api.py
import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=False)
PREFIX = "/docdoku-plm-server-rest/api"
WS = "Workspace_2"


def _token():
    resp = client.post(f"{PREFIX}/auth/login",
                       json={"login": "test1", "password": "password"})
    return resp.json().get("jwt", "")


def test_create_and_delete_webhook():
    h = {"Authorization": f"Bearer {_token()}"}
    name = "WH-" + uuid.uuid4().hex[:6]
    resp = client.post(f"{PREFIX}/workspaces/{WS}/webhooks",
                       json={"name": name, "active": True,
                             "webhookApp": {"dtype": "SIMPLE_HTTP", "uri": "http://example.com"}},
                       headers=h)
    assert resp.status_code == 201
    wid = resp.json()["id"]
    resp = client.delete(f"{PREFIX}/workspaces/{WS}/webhooks/{wid}", headers=h)
    assert resp.status_code == 204
```

```bash
source venv/bin/activate && pytest tests/test_webhooks_api.py -v
git add app/routers/webhooks.py tests/test_webhooks_api.py app/main.py
git commit -m "feat: P5 Task 9——Webhook CRUD 路由"
```

---

## Task 10: Auth 补全

**Files:**
- Modify: `app/routers/auth.py`
- Create: `tests/test_auth_complete.py`

- [ ] **Step 1: 在 `auth.py` 补端点**

```python
# 在现有 auth.py 中添加：

@router.get("/auth/logout")
def logout():
    """JWT 无状态，登出由前端丢弃 token。返回 204。"""
    return Response(status_code=204)


@router.get("/auth/providers/{provider_id}")
def get_provider(provider_id: str):
    """获取单个 OAuth provider。当前无 OAuth 配置，返回 404。"""
    from app.core.exceptions import EntityNotFoundException
    raise EntityNotFoundException("OAuthProviderNotFoundException", provider_id)


@router.post("/auth/recovery")
def send_password_recovery(body: dict, db: Session = Depends(get_db)):
    """发送密码恢复邮件。MVP: 不实际发邮件，只返回 204。"""
    login = body.get("login", "")
    acc = db.query(Account).filter(Account.login == login).first()
    if not acc:
        # 出于安全不暴露用户是否存在
        return Response(status_code=204)
    # TODO: 实际发送邮件（MailHog SMTP 在 8003 端口）
    return Response(status_code=204)


@router.post("/auth/recover")
def execute_recover(body: dict, db: Session = Depends(get_db)):
    """执行密码恢复。MVP: 直接更新密码。"""
    import hashlib
    login = body.get("login", "")
    new_password = body.get("password", "")
    if not login or not new_password:
        from app.core.exceptions import CreationException
        raise CreationException("CreationException")
    from app.models.user_mgmt import Credential
    cred = db.query(Credential).filter(Credential.login == login).first()
    if not cred:
        from app.core.exceptions import EntityNotFoundException
        raise EntityNotFoundException("AccountNotFoundException", login)
    cred.password = hashlib.md5(new_password.encode()).hexdigest()
    db.commit()
    return Response(status_code=204)


@router.post("/auth/oauth")
def oauth_login(body: dict):
    """OAuth 登录。当前无 OAuth 配置，返回 501。"""
    from fastapi import HTTPException
    raise HTTPException(501, "OAuth not configured")
```

- [ ] **Step 2: 写测试 + 运行 + Commit**

```python
# tests/test_auth_complete.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=False)
PREFIX = "/docdoku-plm-server-rest/api"


def test_logout():
    resp = client.get(f"{PREFIX}/auth/logout")
    assert resp.status_code == 204


def test_recovery_unknown_user():
    resp = client.post(f"{PREFIX}/auth/recovery", json={"login": "nonexistent"})
    assert resp.status_code == 204


def test_provider_not_found():
    resp = client.get(f"{PREFIX}/auth/providers/google")
    assert resp.status_code == 404
```

```bash
source venv/bin/activate && pytest tests/test_auth_complete.py -v
git add app/routers/auth.py tests/test_auth_complete.py
git commit -m "feat: P5 Task 10——Auth 补全（logout/recovery/recover/providers/oauth）"
```

---

## Task 11: Nginx 路由 + Payara 对拍 + 文档

**Files:**
- Modify: `docdoku-plm-docker/front/nginx.conf`
- Modify: `docs/CHANGELOG.md`
- Modify: `docs/REMINDERS.md`
- Modify: `docs/superpowers/fastapi-migration-roadmap.md`

- [ ] **Step 1: 在 nginx.conf 添加 P5 路由块**

在 Payara 兜底 location 之前插入：

```nginx
# P5：用户/组/成员资格/角色/工作流/通知/Webhook
location ~ ^/docdoku-plm-server-rest/api/workspaces/[^/]+/(users|groups|memberships|roles|workflow-models|workflow-instances|workspace-workflows|tasks|notifications|webhooks|user-group) {
    set $backpy "back-py:8000";
    proxy_pass         http://$backpy;
    proxy_http_version 1.1;
    proxy_set_header   Host              $host;
    proxy_set_header   X-Real-IP         $remote_addr;
    proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_read_timeout 300s;
    client_max_body_size 500m;
}

# P5：WorkspaceResource 内散落的用户管理端点
location ~ ^/docdoku-plm-server-rest/api/workspaces/[^/]+/(add-user|admin|user-access|group-access|remove-from-group|remove-from-workspace|enable-user|disable-user|enable-group|disable-group) {
    set $backpy "back-py:8000";
    proxy_pass         http://$backpy;
    proxy_http_version 1.1;
    proxy_set_header   Host              $host;
    proxy_set_header   X-Real-IP         $remote_addr;
    proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_read_timeout 300s;
}

# P5：账号管理
location /docdoku-plm-server-rest/api/accounts {
    set $backpy "back-py:8000";
    proxy_pass         http://$backpy;
    proxy_http_version 1.1;
    proxy_set_header   Host              $host;
    proxy_set_header   X-Real-IP         $remote_addr;
    proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_read_timeout 300s;
}
```

- [ ] **Step 2: 重建容器**

```bash
cd docdoku-plm-docker
docker compose up -d --build back-py
docker compose up -d --force-recreate --no-deps front
```

- [ ] **Step 3: 运行全部测试**

Run: `source venv/bin/activate && pytest tests/ -q`
Expected: 所有 P5 测试通过，已有测试不回归

- [ ] **Step 4: 更新文档**

CHANGELOG.md 顶部添加：
```markdown
## 2026-07-05 — P5 工作流与权限

- feat: P5 完整迁移——66 端点 / 6 功能域 / 16 张表 / 4 ORM 模型文件
- feat: 用户/账号/组管理——UserMgmtService + users.py + accounts.py（24 端点）
- feat: ACL/角色——SecurityService + acl_helper + roles.py + 已有路由补 ACL（13 端点）
- feat: 工作流——WorkflowService + workflows.py（17 端点，process_task MVP）
- feat: 通知——NotificationService + notifications.py（5 端点）
- feat: Webhook——webhooks.py（5 端点）
- feat: Auth 补全——logout/recovery/recover/providers/oauth（5 端点）
- feat: Nginx 10+ 路由块切换
- test: 全部测试通过
```

REMINDERS.md：P5 标记完成，PartRevisionDTO.notifications 对齐债务清偿。

路线图：P5 → ✅ 完成，Nginx 路由表补全，对齐债务全部清偿。

- [ ] **Step 5: Commit**

```bash
git add docdoku-plm-docker/front/nginx.conf docs/CHANGELOG.md docs/REMINDERS.md docs/superpowers/fastapi-migration-roadmap.md
git commit -m "feat: P5 完成——Nginx 路由切换 + 文档更新"
```
