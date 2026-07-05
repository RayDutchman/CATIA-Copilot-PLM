# P4 变更管理 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现变更管理 4 类实体（ChangeIssue/Request/Order/Milestone）的 CRUD + 标签管理，行为与 Payara 一致，前端零改动。

**Architecture:** 单 ORM 模型文件、单 service、单路由文件覆盖全部 ~30 端点。模式高度重复（4 类型 × 相同 CRUD），service 层用统一模板。

**Tech Stack:** FastAPI、SQLAlchemy、Pydantic v2、pytest。

## Global Constraints

- API 路径前缀 `/docdoku-plm-server-rest/api` 不变，前端 Backbone.js 零改动。
- 运行测试：`workdir: docdoku-plm-server-py` → `source venv/bin/activate && pytest tests/ -q`。
- 重建容器：`workdir: docdoku-plm-docker` → `docker compose up -d --build back-py`。
- 测试数据：test1/password 是 `Workspace_2` 成员且 language=zh。
- 异常复用 `app/core/exceptions.py`，抛 i18n key，禁止硬编码消息。
- 遵循标准每阶段工作流 + 防御清单 #0（前端 Model 审计）。
- Conventional Commits 提交信息。
- 所有变更表当前为空（DB 无预存数据）。

---

## 文件结构

**新建：**
- `app/models/change.py` — ChangeIssue/ChangeRequest/ChangeOrder/Milestone ORM + 标签关联表
- `app/routers/changes.py` — 30 端点（单路由文件）
- `app/services/change_service.py` — 通用 CRUD
- `tests/test_change_models.py`、`tests/test_change_service.py`、`tests/test_changes_api.py`

**修改：**
- `app/main.py` — 注册 changes 路由
- `docdoku-plm-docker/front/nginx.conf` — 1 条 location 正则块

---

## Task 1: ORM 模型

**Files:**
- Create: `docdoku-plm-server-py/app/models/change.py`
- Test: `docdoku-plm-server-py/tests/test_change_models.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_change_models.py
from app.models.change import ChangeIssue, ChangeRequest, ChangeOrder, Milestone


def test_tables_exist():
    assert ChangeIssue.__tablename__ == "changeissue"
    assert ChangeRequest.__tablename__ == "changerequest"
    assert ChangeOrder.__tablename__ == "changeorder"
    assert Milestone.__tablename__ == "milestone"
```

- [ ] **Step 2: 运行确认失败** `pytest tests/test_change_models.py -q`

- [ ] **Step 3: 实现 `app/models/change.py`**

```python
from typing import Optional, List
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, ForeignKeyConstraint, Table
from sqlalchemy.orm import relationship, Mapped
from app.core.database import Base

# ── 标签关联表 ─────────────────────────────────────────────

change_issue_tags = Table(
    "changeissue_tag", Base.metadata,
    Column("changeissue_id", Integer, ForeignKey("changeissue.id"), primary_key=True),
    Column("tag_workspace_id", String, primary_key=True),
    Column("tag_label", String, primary_key=True),
)

change_request_tags = Table(
    "changerequest_tag", Base.metadata,
    Column("changerequest_id", Integer, ForeignKey("changerequest.id"), primary_key=True),
    Column("tag_workspace_id", String, primary_key=True),
    Column("tag_label", String, primary_key=True),
)

change_order_tags = Table(
    "changeorder_tag", Base.metadata,
    Column("changeorder_id", Integer, ForeignKey("changeorder.id"), primary_key=True),
    Column("tag_workspace_id", String, primary_key=True),
    Column("tag_label", String, primary_key=True),
)

# ── ChangeIssue ────────────────────────────────────────────

class ChangeIssue(Base):
    __tablename__ = "changeissue"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(Text)
    initiator = Column(String)
    category = Column(Integer)
    priority = Column(Integer)
    creation_date = Column("creationdate", DateTime)
    assignee_workspace_id = Column(String)
    assignee_login = Column(String)
    author_workspace_id = Column(String)
    author_login = Column(String)
    workspace_id = Column(String)
    acl_id = Column(Integer)

    tags: Mapped[List["Tag"]] = relationship(
        "Tag", secondary=change_issue_tags)

# ── ChangeRequest ──────────────────────────────────────────

class ChangeRequest(Base):
    __tablename__ = "changerequest"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(Text)
    category = Column(Integer)
    priority = Column(Integer)
    creation_date = Column("creationdate", DateTime)
    milestone_id = Column(Integer)
    assignee_workspace_id = Column(String)
    assignee_login = Column(String)
    author_workspace_id = Column(String)
    author_login = Column(String)
    workspace_id = Column(String)
    acl_id = Column(Integer)

    tags: Mapped[List["Tag"]] = relationship(
        "Tag", secondary=change_request_tags)

# ── ChangeOrder ─────────────────────────────────────────────

class ChangeOrder(Base):
    __tablename__ = "changeorder"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(Text)
    category = Column(Integer)
    priority = Column(Integer)
    creation_date = Column("creationdate", DateTime)
    milestone_id = Column(Integer)
    assignee_workspace_id = Column(String)
    assignee_login = Column(String)
    author_workspace_id = Column(String)
    author_login = Column(String)
    workspace_id = Column(String)
    acl_id = Column(Integer)

    tags: Mapped[List["Tag"]] = relationship(
        "Tag", secondary=change_order_tags)

# ── Milestone ───────────────────────────────────────────────

class Milestone(Base):
    __tablename__ = "milestone"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    description = Column(Text)
    due_date = Column("duedate", DateTime)
    workspace_id = Column(String)
    acl_id = Column(Integer)

from app.models.part import Tag  # noqa
```

- [ ] **Step 4: 运行确认通过** `pytest tests/test_change_models.py -q`

- [ ] **Step 5: Commit**

```bash
git add docdoku-plm-server-py/app/models/change.py docdoku-plm-server-py/tests/test_change_models.py
git commit -m "feat(py): 变更管理 ORM——ChangeIssue/Request/Order/Milestone + 标签关联表"
```

---

## Task 2: change_service

**Files:**
- Create: `docdoku-plm-server-py/app/services/change_service.py`
- Test: `docdoku-plm-server-py/tests/test_change_service.py`

**Interfaces:**

- `_cls(type)` → 返回对应 ORM 类
- `get_by_id(db, cls, ws, id)` → 单条或 404
- 通用 CRUD：`list_items / create_item / update_item / delete_item`
- 标签：`set_tags / add_tag / remove_tag`

**请求体字段映射**（前端发 camelCase）：

| 前端字段 | Model 字段 |
|----------|-----------|
| `name` | `name` |
| `description` | `description` |
| `priority` | `priority`（integer）|
| `assignee` | `{"login":"x"}` → `assignee_login` |

- [ ] **Step 1: 写失败测试**

```python
# tests/test_change_service.py
from app.services.change_service import ChangeService
WS = "Workspace_2"
svc = ChangeService()


def test_issue_crud(db):
    it = svc.create_item(db, WS, "issue",
                         name="Test Issue", description="desc",
                         author_login="test1", user_login="test1")
    assert it.name == "Test Issue"
    found = svc.get_by_id(db, ChangeIssue, WS, it.id)
    assert found.name == "Test Issue"
    svc.delete_item(db, ChangeIssue, WS, it.id)
```

- [ ] **Step 2: 运行→FAIL→实现→PASS→Commit**

---

## Task 3: changes 路由

**Files:**
- Create: `docdoku-plm-server-py/app/routers/changes.py` + `tests/test_changes_api.py`
- Modify: `app/main.py`

**路由结构**：一个 router 覆盖所有端点，关键路由在 `{id}` 之前：

```python
# 固定路径在前
GET  /workspaces/{ws}/changes/issues        # list
POST /workspaces/{ws}/changes/issues        # create
GET  /workspaces/{ws}/changes/requests
POST /workspaces/{ws}/changes/requests
GET  /workspaces/{ws}/changes/orders
POST /workspaces/{ws}/changes/orders
GET  /workspaces/{ws}/changes/milestones
POST /workspaces/{ws}/changes/milestones
# 参数路径在后（{id}）
GET    /workspaces/{ws}/changes/issues/{id}
PUT    /workspaces/{ws}/changes/issues/{id}
DELETE /workspaces/{ws}/changes/issues/{id}
PUT    /workspaces/{ws}/changes/issues/{id}/tags
POST   /workspaces/{ws}/changes/issues/{id}/tags
DELETE /workspaces/{ws}/changes/issues/{id}/tags/{tag_label}
# ... 同样 pattern for requests/orders/milestones
```

- [ ] **Step 1: TDD→实现→全量测试 86+→Commit**

---

## Task 4: 对齐审计 + Payara 对拍 + 切 Nginx

**Files:**
- Modify: `docdoku-plm-docker/front/nginx.conf`

**Nginx 新增**（在兜底 Payara 之前）：

```nginx
    # P4：变更管理端点迁移到 FastAPI back-py
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

- [ ] **Step 1: Payara 对拍**（创建/列表/详情对比 8001 vs 8000）
- [ ] **Step 2: 全量测试 + 重建 back-py + front**
- [ ] **Step 3: 前端实测清单**（建 Issue→CRUD→Milestones）
- [ ] **Step 4: 更新文档 + Commit**

---

## 前端实测清单

1. 创建变更 Issue→编辑→删除
2. 创建变更 Request→关联 Issue→删除
3. 创建变更 Order→关联 Request→删除
4. 创建 Milestone→关联 Order/Request→删除
5. 打标签→删标签

---

## Self-Review

- **Spec 覆盖**：前端 Model 审计（Task 0 ✅ 无风险）、ORM（Task 1 ✅）、Service（Task 2 ✅）、路由（Task 3 ✅）、对拍+Nginx（Task 4 ✅）。
- **Placeholder 扫描**：无 TBD/TODO。
- **类型一致**：ChangeService 所有方法签名全计划一致。
