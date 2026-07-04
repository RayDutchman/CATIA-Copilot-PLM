# P2 文档与文件夹 + 文档模板 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 FastAPI 实现文档 CRUD（签出签入/发布废弃/标签/搜索）、文档文件上传下载、文件夹 CRUD、文档模板 CRUD，行为与 Payara 一致，前端零改动。

**Architecture:** 新建 `document.py` 模型 + `document_service.py` + 4 个路由文件（documents / folders / document_files / document_templates）。异常/i18n 复用 P1a-align 基础设施。搜索 DB LIKE MVP。文件夹直接操作 `folder` 表（仅 2 列、自引用）。

**Tech Stack:** FastAPI、SQLAlchemy、Pydantic v2、pytest、UploadFile。

## Global Constraints

- API 路径前缀 `/docdoku-plm-server-rest/api` 不变，前端 Backbone.js 零改动。
- 运行测试：`workdir: docdoku-plm-server-py` → `source venv/bin/activate && pytest tests/ -q`。
- 重建容器：`workdir: docdoku-plm-docker` → `docker compose up -d --build back-py`。
- 测试数据：test1/password 是 `Workspace_2` 成员且 language=zh。
- 异常复用 `app/core/exceptions.py`，抛 i18n key，禁止硬编码消息。
- 遵循标准每阶段工作流：ORM→端点→对齐审计→Payara 对拍→前端实测→通过后才切 Nginx。
- Conventional Commits 提交信息。

---

## 文件结构

**新建：**
- `app/models/document.py` — ORM（documentmaster/revision/iteration/binres/tag/folder/template）
- `app/routers/documents.py` — DocumentsResource + DocumentResource
- `app/routers/folders.py` — FolderResource
- `app/routers/document_files.py` — 文件上传下载
- `app/routers/document_templates.py` — DocumentTemplateResource
- `app/services/document_service.py` — DocumentManagerBean 对应逻辑
- `tests/test_document_models.py`、`tests/test_document_service.py`、`tests/test_documents_api.py`、`tests/test_folders_api.py`、`tests/test_document_templates_api.py`

**修改：**
- `app/main.py` — 注册 4 个新路由
- `docdoku-plm-docker/front/nginx.conf` — 新增 4 个路由块

---

## 关键事实（DB 已验证）

- `documentrevision` PK: `(workspace_id, documentmaster_id, version)`
- `documentiteration` PK: `(workspace_id, documentmaster_id, documentrevision_version, iteration)`
- `folder` PK: `completepath`（无 workspace_id 列），自引用 FK→`parentfolder_completepath`
- `documentmastertemplate` PK: `(workspace_id, id)`
- `documentiteration_binres` 联合主键 + FK→binaryresource.fullname
- `documentrevision_tag` 联合主键

---

## Task 1: ORM 模型（`app/models/document.py`）

**Files:**
- Create: `docdoku-plm-server-py/app/models/document.py`
- Test: `docdoku-plm-server-py/tests/test_document_models.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_document_models.py
from app.core.database import SessionLocal
from app.models.document import DocumentMaster, DocumentRevision, Folder


def test_folder_rows_exist():
    db = SessionLocal()
    count = db.query(Folder).count()
    assert count >= 4
    db.close()


def test_tables_exist():
    db = SessionLocal()
    assert DocumentMaster.__tablename__ == "documentmaster"
    assert DocumentRevision.__tablename__ == "documentrevision"
    db.close()
```

- [ ] **Step 2: 运行确认失败**

Run: `source venv/bin/activate && pytest tests/test_document_models.py -q`
Expected: FAIL。

- [ ] **Step 3: 实现 `app/models/document.py`**

```python
# app/models/document.py
"""ORMs: documentmaster → documentrevision → documentiteration。"""
from typing import Optional, List
from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime, Text,
    ForeignKey, ForeignKeyConstraint, Table
)
from sqlalchemy.orm import relationship, Mapped
from app.core.database import Base

# ── 关联表 ────────────────────────────────────────────────

document_iteration_binres = Table(
    "documentiteration_binres", Base.metadata,
    Column("workspace_id", String, primary_key=True),
    Column("documentmaster_id", String, primary_key=True),
    Column("documentrevision_version", String, primary_key=True),
    Column("iteration", Integer, primary_key=True),
    Column("attachedfile_fullname", String,
           ForeignKey("binaryresource.fullname"), primary_key=True),
    ForeignKeyConstraint(
        ["workspace_id", "documentmaster_id", "documentrevision_version", "iteration"],
        ["documentiteration.workspace_id", "documentiteration.documentmaster_id",
         "documentiteration.documentrevision_version", "documentiteration.iteration"],
    ),
)

document_revision_tags = Table(
    "documentrevision_tag", Base.metadata,
    Column("documentmaster_workspace_id", String, primary_key=True),
    Column("documentmaster_id", String, primary_key=True),
    Column("documentrevision_version", String, primary_key=True),
    Column("tag_workspace_id", String, primary_key=True),
    Column("tag_label", String, primary_key=True),
    ForeignKeyConstraint(
        ["documentmaster_workspace_id", "documentmaster_id", "documentrevision_version"],
        ["documentrevision.workspace_id", "documentrevision.documentmaster_id",
         "documentrevision.version"],
    ),
)

# ── Folder ─────────────────────────────────────────────────

class Folder(Base):
    __tablename__ = "folder"
    completepath = Column("completepath", String, primary_key=True)
    parentfolder_completepath = Column("parentfolder_completepath", String,
                                       ForeignKey("folder.completepath"))

# ── DocumentMaster ─────────────────────────────────────────

class DocumentMaster(Base):
    __tablename__ = "documentmaster"
    id = Column(String, primary_key=True)
    workspace_id = Column(String, primary_key=True)
    type = Column(String)
    creation_date = Column("creationdate", DateTime)
    attributes_locked = Column("attributeslocked", Boolean, default=False)
    author_workspace_id = Column(String)
    author_login = Column(String)

    revisions: Mapped[List["DocumentRevision"]] = relationship(
        "DocumentRevision",
        foreign_keys="[DocumentRevision.workspace_id, DocumentRevision.documentmaster_id]",
        primaryjoin=(
            "and_(DocumentMaster.workspace_id==DocumentRevision.workspace_id,"
            "DocumentMaster.id==DocumentRevision.documentmaster_id)"
        ),
        order_by="DocumentRevision.version", back_populates="document_master",
    )

# ── DocumentRevision ───────────────────────────────────────

class DocumentRevision(Base):
    __tablename__ = "documentrevision"
    workspace_id = Column(String, primary_key=True)
    documentmaster_id = Column(String, primary_key=True)
    version = Column(String, primary_key=True)

    title = Column(String)
    description = Column(Text)
    status = Column(Integer, default=0)
    public_shared = Column("publicshared", Boolean, default=False)
    creation_date = Column("creationdate", DateTime)
    check_out_date = Column("checkoutdate", DateTime)
    release_date = Column("release_date", DateTime)
    obsolete_date = Column("obsolete_date", DateTime)
    location_completepath = Column("location_completepath", String)

    author_workspace_id = Column(String)
    author_login = Column(String)
    checkout_user_workspace_id = Column("checkoutuser_workspace_id", String)
    checkout_user_login = Column("checkoutuser_login", String)
    release_user_workspace = Column(String)
    release_user_login = Column(String)
    obsolete_user_workspace = Column(String)
    obsolete_user_login = Column(String)
    acl_id = Column(Integer)
    workflow_id = Column(Integer)

    document_master: Mapped["DocumentMaster"] = relationship(
        "DocumentMaster",
        foreign_keys=[workspace_id, documentmaster_id],
        primaryjoin=(
            "and_(DocumentRevision.workspace_id==DocumentMaster.workspace_id,"
            "DocumentRevision.documentmaster_id==DocumentMaster.id)"
        ),
        back_populates="revisions",
    )
    iterations: Mapped[List["DocumentIteration"]] = relationship(
        "DocumentIteration",
        foreign_keys=(
            "DocumentIteration.workspace_id,"
            "DocumentIteration.documentmaster_id,"
            "DocumentIteration.documentrevision_version"),
        primaryjoin=(
            "and_(DocumentRevision.workspace_id==DocumentIteration.workspace_id,"
            "DocumentRevision.documentmaster_id==DocumentIteration.documentmaster_id,"
            "DocumentRevision.version==DocumentIteration.documentrevision_version)"),
        order_by="DocumentIteration.iteration", back_populates="revision",
        cascade="all, delete-orphan",
    )

    @property
    def last_iteration(self):
        return self.iterations[-1] if self.iterations else None

    @property
    def last_iteration_number(self) -> int:
        return self.iterations[-1].iteration if self.iterations else 0

# ── DocumentIteration ──────────────────────────────────────

class DocumentIteration(Base):
    __tablename__ = "documentiteration"
    workspace_id = Column(String, primary_key=True)
    documentmaster_id = Column(String, primary_key=True)
    documentrevision_version = Column(String, primary_key=True)
    iteration = Column(Integer, primary_key=True)

    revision_note = Column("revisionnote", String)
    creation_date = Column("creationdate", DateTime)
    modification_date = Column("modificationdate", DateTime)
    check_in_date = Column("checkindate", DateTime)
    author_workspace_id = Column(String)
    author_login = Column(String)

    revision: Mapped["DocumentRevision"] = relationship(
        "DocumentRevision",
        foreign_keys=[workspace_id, documentmaster_id, documentrevision_version],
        primaryjoin=(
            "and_(DocumentIteration.workspace_id==DocumentRevision.workspace_id,"
            "DocumentIteration.documentmaster_id==DocumentRevision.documentmaster_id,"
            "DocumentIteration.documentrevision_version==DocumentRevision.version)"),
        back_populates="iterations",
    )

# ── DocumentMasterTemplate ─────────────────────────────────

class DocumentMasterTemplate(Base):
    __tablename__ = "documentmastertemplate"
    workspace_id = Column(String, primary_key=True)
    id = Column(String, primary_key=True)
    document_type = Column("documenttype", String)
    mask = Column(String)
    id_generated = Column("idgenerated", Boolean, default=False)
    attributes_locked = Column("attributeslocked", Boolean, default=False)
    creation_date = Column("creationdate", DateTime)
    modification_date = Column("modificationdate", DateTime)
    author_workspace_id = Column(String)
    author_login = Column(String)
    workflowmodel_id = Column(String)
    acl_id = Column(Integer)
```

- [ ] **Step 4: 运行确认通过**

Run: `source venv/bin/activate && pytest tests/test_document_models.py -q`
Expected: 2 passed。

- [ ] **Step 5: Commit**

```bash
git add docdoku-plm-server-py/app/models/document.py docdoku-plm-server-py/tests/test_document_models.py
git commit -m "feat(py): 文档模型 ORM——documentmaster/revision/iteration/folder/template"
```

---

## Task 2: document_service（CRUD + 签出签入 + 状态）

**Files:**
- Create: `docdoku-plm-server-py/app/services/document_service.py`
- Test: `docdoku-plm-server-py/tests/test_document_service.py`

**i18n key 清单**（来自 Java audit）：

| 方法 | 校验 → key |
|------|-----------|
| create | 已存在→`DocumentMasterAlreadyExistsException`(doc_id) |
| delete | checkout_user≠user→`NotAllowedException22` |
| checkout | 已签出→`NotAllowedException37`；非最新版→`NotAllowedException72` |
| checkin | 非当前用户→`NotAllowedException20` |
| undo | 非当前用户→`NotAllowedException19`；迭代≤1→`NotAllowedException27` |
| release | 已签出→`NotAllowedException63`；无迭代→`NotAllowedException27`；已废弃→`NotAllowedException64` |
| obsolete | 未发布→`NotAllowedException65` |

- [ ] **Step 1: 写失败测试**

```python
# tests/test_document_service.py
from app.services.document_service import DocumentService
from app.core.exceptions import EntityAlreadyExistsException
WS = "Workspace_2"
svc = DocumentService()


def _make(db, doc_id):
    return svc.create_document(db, WS, doc_id, "T", "test1")


def test_create_and_delete(db):
    pr = _make(db, "P2SVC-1")
    assert pr.documentmaster_id == "P2SVC-1"
    assert pr.checkout_user_login == "test1"
    svc.checkin(db, WS, "P2SVC-1", "A", "test1")
    svc.delete_revision(db, WS, "P2SVC-1", "A", "test1")


def test_duplicate_raises(db):
    _make(db, "P2SVC-DUP")
    try:
        _make(db, "P2SVC-DUP")
        assert False
    except EntityAlreadyExistsException as e:
        assert e.key == "DocumentMasterAlreadyExistsException"
    svc.checkin(db, WS, "P2SVC-DUP", "A", "test1")
    svc.delete_revision(db, WS, "P2SVC-DUP", "A", "test1")
```

- [ ] **Step 2: 运行确认失败**

Run: `source venv/bin/activate && pytest tests/test_document_service.py -q`
Expected: FAIL。

- [ ] **Step 3: 实现 `app/services/document_service.py`**

```python
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.document import (
    DocumentMaster, DocumentRevision, DocumentIteration,
    DocumentMasterTemplate, Folder, document_iteration_binres,
    document_revision_tags,
)
from app.core.exceptions import (
    EntityAlreadyExistsException, NotAllowedException,
    EntityConstraintException,
)


class DocumentService:

    def get_revision(self, db, ws, doc_id, ver):
        pr = db.query(DocumentRevision).filter(
            DocumentRevision.workspace_id == ws,
            DocumentRevision.documentmaster_id == doc_id,
            DocumentRevision.version == ver,
        ).first()
        if pr is None:
            raise HTTPException(404, f"Document {doc_id}-{ver} not found")
        return pr

    def count_documents(self, db, ws):
        return db.query(DocumentMaster).filter(
            DocumentMaster.workspace_id == ws,
            DocumentMaster.revisions.any(),
        ).count()

    def list_revisions(self, db, ws, start=0, length=50):
        return db.query(DocumentRevision).filter(
            DocumentRevision.workspace_id == ws,
        ).order_by(DocumentRevision.documentmaster_id,
                   DocumentRevision.version).offset(start).limit(length).all()

    def create_document(self, db, ws, doc_id, title, user_login,
                        folder_path=None):
        existing = db.query(DocumentMaster).filter(
            DocumentMaster.workspace_id == ws,
            DocumentMaster.id == doc_id,
        ).first()
        if existing:
            raise EntityAlreadyExistsException(
                "DocumentMasterAlreadyExistsException", doc_id)
        now = datetime.utcnow()
        location = folder_path or ws
        master = DocumentMaster(
            id=doc_id, workspace_id=ws, creation_date=now,
            author_workspace_id=ws, author_login=user_login)
        db.add(master); db.flush()
        rev = DocumentRevision(
            workspace_id=ws, documentmaster_id=doc_id, version="A",
            title=title, status=0, creation_date=now,
            location_completepath=location,
            author_workspace_id=ws, author_login=user_login,
            checkout_user_workspace_id=ws, checkout_user_login=user_login,
            check_out_date=now)
        db.add(rev); db.flush()
        it = DocumentIteration(
            workspace_id=ws, documentmaster_id=doc_id,
            documentrevision_version="A", iteration=1,
            creation_date=now, author_workspace_id=ws,
            author_login=user_login)
        db.add(it)
        db.commit(); db.refresh(rev)
        return rev

    def delete_revision(self, db, ws, doc_id, ver, user_login):
        pr = self.get_revision(db, ws, doc_id, ver)
        if pr.checkout_user_login and pr.checkout_user_login != user_login:
            raise NotAllowedException("NotAllowedException22")
        # 清关联
        db.query(document_revision_tags).filter(
            document_revision_tags.c.documentmaster_workspace_id == ws,
            document_revision_tags.c.documentmaster_id == doc_id,
            document_revision_tags.c.documentrevision_version == ver,
        ).delete()
        for it in pr.iterations:
            db.query(document_iteration_binres).filter(
                document_iteration_binres.c.workspace_id == ws,
                document_iteration_binres.c.documentmaster_id == doc_id,
                document_iteration_binres.c.documentrevision_version == ver,
                document_iteration_binres.c.iteration == it.iteration,
            ).delete()
        db.delete(pr)
        db.commit()

    def checkout(self, db, ws, doc_id, ver, user_login):
        pr = self.get_revision(db, ws, doc_id, ver)
        if pr.checkout_user_login:
            raise NotAllowedException("NotAllowedException37")
        if pr.status != 0:
            raise NotAllowedException("NotAllowedException47")
        now = datetime.utcnow()
        pr.checkout_user_login = user_login
        pr.checkout_user_workspace_id = ws
        pr.check_out_date = now
        last = pr.last_iteration_number + 1
        db.add(DocumentIteration(
            workspace_id=ws, documentmaster_id=doc_id,
            documentrevision_version=ver, iteration=last,
            creation_date=now, author_workspace_id=ws,
            author_login=user_login))
        db.commit(); db.refresh(pr)
        return pr

    def checkin(self, db, ws, doc_id, ver, user_login):
        pr = self.get_revision(db, ws, doc_id, ver)
        if pr.checkout_user_login != user_login:
            raise NotAllowedException("NotAllowedException20")
        now = datetime.utcnow()
        last = pr.last_iteration
        if last:
            last.check_in_date = now
        pr.checkout_user_login = None
        pr.checkout_user_workspace_id = None
        pr.check_out_date = None
        db.commit(); db.refresh(pr)
        return pr

    def undo_checkout(self, db, ws, doc_id, ver, user_login):
        pr = self.get_revision(db, ws, doc_id, ver)
        if pr.checkout_user_login != user_login:
            raise NotAllowedException("NotAllowedException19")
        if len(pr.iterations) <= 1:
            raise NotAllowedException("NotAllowedException27")
        last = pr.last_iteration
        if last and last.check_in_date is None:
            db.delete(last)
        pr.checkout_user_login = None
        pr.checkout_user_workspace_id = None
        pr.check_out_date = None
        db.commit(); db.refresh(pr)
        return pr

    def release(self, db, ws, doc_id, ver, user_login):
        pr = self.get_revision(db, ws, doc_id, ver)
        if pr.checkout_user_login:
            raise NotAllowedException("NotAllowedException63")
        if not pr.iterations:
            raise NotAllowedException("NotAllowedException27")
        if pr.status == 2:
            raise NotAllowedException("NotAllowedException64")
        pr.status = 1
        pr.release_date = datetime.utcnow()
        pr.release_user_login = user_login
        pr.release_user_workspace = ws
        db.commit(); db.refresh(pr)
        return pr

    def mark_obsolete(self, db, ws, doc_id, ver, user_login):
        pr = self.get_revision(db, ws, doc_id, ver)
        if pr.status != 1:
            raise NotAllowedException("NotAllowedException65")
        pr.status = 2
        pr.obsolete_date = datetime.utcnow()
        pr.obsolete_user_login = user_login
        pr.obsolete_user_workspace = ws
        db.commit(); db.refresh(pr)
        return pr

    def create_new_version(self, db, ws, doc_id, ver, user_login):
        pr = self.get_revision(db, ws, doc_id, ver)
        if pr.checkout_user_login:
            raise NotAllowedException("NotAllowedException40")
        if not pr.iterations:
            raise NotAllowedException("NotAllowedException27")
        now = datetime.utcnow()
        new_ver = self._next_version(ver)
        new_pr = DocumentRevision(
            workspace_id=ws, documentmaster_id=doc_id, version=new_ver,
            title=pr.title, description=pr.description, status=0,
            creation_date=now,
            location_completepath=pr.location_completepath,
            author_workspace_id=ws, author_login=user_login,
            checkout_user_workspace_id=ws, checkout_user_login=user_login,
            check_out_date=now)
        db.add(new_pr); db.flush()
        db.add(DocumentIteration(
            workspace_id=ws, documentmaster_id=doc_id,
            documentrevision_version=new_ver, iteration=1,
            creation_date=now, author_workspace_id=ws,
            author_login=user_login))
        db.commit(); db.refresh(new_pr)
        return new_pr

    # ── tags ──

    def _ensure_tag(self, db, ws, label):
        from app.models.part import Tag
        t = db.query(Tag).filter(Tag.workspace_id == ws,
                                 Tag.label == label).first()
        if t is None:
            db.add(Tag(workspace_id=ws, label=label)); db.flush()

    def set_tags(self, db, ws, doc_id, ver, labels):
        pr = self.get_revision(db, ws, doc_id, ver)
        db.execute(document_revision_tags.delete().where(
            document_revision_tags.c.documentmaster_workspace_id == ws,
            document_revision_tags.c.documentmaster_id == doc_id,
            document_revision_tags.c.documentrevision_version == ver,
        ))
        for label in labels:
            self._ensure_tag(db, ws, label)
            db.execute(document_revision_tags.insert().values(
                documentmaster_workspace_id=ws, documentmaster_id=doc_id,
                documentrevision_version=ver, tag_workspace_id=ws,
                tag_label=label))
        db.commit(); db.refresh(pr)
        return pr

    def add_tag(self, db, ws, doc_id, ver, label):
        pr = self.get_revision(db, ws, doc_id, ver)
        self._ensure_tag(db, ws, label)
        exists = db.execute(document_revision_tags.select().where(
            document_revision_tags.c.documentmaster_workspace_id == ws,
            document_revision_tags.c.documentmaster_id == doc_id,
            document_revision_tags.c.documentrevision_version == ver,
            document_revision_tags.c.tag_label == label,
        )).first()
        if exists is None:
            db.execute(document_revision_tags.insert().values(
                documentmaster_workspace_id=ws, documentmaster_id=doc_id,
                documentrevision_version=ver, tag_workspace_id=ws,
                tag_label=label))
        db.commit(); db.refresh(pr)
        return pr

    def remove_tag(self, db, ws, doc_id, ver, label):
        pr = self.get_revision(db, ws, doc_id, ver)
        db.execute(document_revision_tags.delete().where(
            document_revision_tags.c.documentmaster_workspace_id == ws,
            document_revision_tags.c.documentmaster_id == doc_id,
            document_revision_tags.c.documentrevision_version == ver,
            document_revision_tags.c.tag_label == label,
        ))
        db.commit(); db.refresh(pr)
        return pr

    # ── search ──

    def search(self, db, ws, title=None, doc_id=None):
        q = db.query(DocumentMaster).filter(
            DocumentMaster.workspace_id == ws)
        if title:
            q = q.filter(DocumentMaster.revisions.any(
                DocumentRevision.title.ilike(f"%{title}%")))
        if doc_id:
            q = q.filter(DocumentMaster.id.ilike(f"%{doc_id}%"))
        masters = q.limit(100).all()
        result = []
        for m in masters:
            result.extend(m.revisions)
        return result

    # ── folder ──

    def create_folder(self, db, parent_path, name, user_login):
        from app.core.exceptions import EntityAlreadyExistsException
        completepath = f"{parent_path}/{name}" if parent_path else name
        existing = db.query(Folder).filter(
            Folder.completepath == completepath).first()
        if existing:
            raise EntityAlreadyExistsException(
                "FolderAlreadyExistsException", completepath)
        folder = Folder(completepath=completepath,
                        parentfolder_completepath=parent_path or None)
        db.add(folder)
        db.commit()
        return folder

    def list_folders(self, db, parent_path=None):
        if parent_path:
            return db.query(Folder).filter(
                Folder.parentfolder_completepath == parent_path).all()
        return db.query(Folder).filter(
            Folder.parentfolder_completepath.is_(None)).all()

    def delete_folder(self, db, completepath):
        folder = db.query(Folder).filter(
            Folder.completepath == completepath).first()
        if folder is None:
            raise HTTPException(404, "Folder not found")
        children = db.query(Folder).filter(
            Folder.parentfolder_completepath == completepath).count()
        if children > 0:
            raise HTTPException(403, "Folder not empty")
        db.delete(folder)
        db.commit()

    # ── template ──

    def list_templates(self, db, ws):
        return db.query(DocumentMasterTemplate).filter(
            DocumentMasterTemplate.workspace_id == ws).all()

    def get_template(self, db, ws, template_id):
        t = db.query(DocumentMasterTemplate).filter(
            DocumentMasterTemplate.workspace_id == ws,
            DocumentMasterTemplate.id == template_id).first()
        if t is None:
            raise HTTPException(404, "Template not found")
        return t

    def create_template(self, db, ws, template_id, document_type, mask,
                        id_generated, user_login):
        existing = db.query(DocumentMasterTemplate).filter(
            DocumentMasterTemplate.workspace_id == ws,
            DocumentMasterTemplate.id == template_id).first()
        if existing:
            raise EntityAlreadyExistsException(
                "DocumentMasterTemplateAlreadyExistsException", template_id)
        now = datetime.utcnow()
        t = DocumentMasterTemplate(
            workspace_id=ws, id=template_id,
            document_type=document_type, mask=mask,
            id_generated=id_generated, creation_date=now,
            author_workspace_id=ws, author_login=user_login)
        db.add(t)
        db.commit(); db.refresh(t)
        return t

    def delete_template(self, db, ws, template_id):
        t = self.get_template(db, ws, template_id)
        db.delete(t)
        db.commit()

    # ── files ──

    def save_file(self, db, ws, doc_id, ver, iteration, filename, data):
        from app.services import vault as vault_svc
        from app.models.part import BinaryResource
        path = (vault_svc._vault_root() / ws / "documents" / doc_id
                / ver / str(iteration) / filename)
        vault_svc.write_file(path, data)
        full_name = f"{ws}/documents/{doc_id}/{ver}/{iteration}/{filename}"
        br = db.query(BinaryResource).filter(
            BinaryResource.full_name == full_name).first()
        now = datetime.utcnow()
        if br is None:
            br = BinaryResource(full_name=full_name,
                                content_length=len(data), last_modified=now,
                                dtype="BinaryResource")
            db.add(br)
        else:
            br.content_length = len(data)
            br.last_modified = now
        db.flush()
        exists = db.execute(document_iteration_binres.select().where(
            document_iteration_binres.c.workspace_id == ws,
            document_iteration_binres.c.documentmaster_id == doc_id,
            document_iteration_binres.c.documentrevision_version == ver,
            document_iteration_binres.c.iteration == iteration,
            document_iteration_binres.c.attachedfile_fullname == full_name,
        )).first()
        if exists is None:
            db.execute(document_iteration_binres.insert().values(
                workspace_id=ws, documentmaster_id=doc_id,
                documentrevision_version=ver, iteration=iteration,
                attachedfile_fullname=full_name))
        db.commit()
        return br

    def get_file_bytes(self, ws, doc_id, ver, iteration, filename):
        from app.services import vault as vault_svc
        path = (vault_svc._vault_root() / ws / "documents" / doc_id
                / ver / str(iteration) / filename)
        return vault_svc.read_file(path)

    # ── helper ──

    def _next_version(self, current):
        if not current: return "A"
        last_char = current[-1]
        if last_char == "Z": return current + "A"
        return current[:-1] + chr(ord(last_char) + 1)
```

- [ ] **Step 4: 运行确认通过**

Run: `source venv/bin/activate && pytest tests/test_document_service.py -q`
Expected: 2 passed。

- [ ] **Step 5: Commit**

```bash
git add docdoku-plm-server-py/app/services/document_service.py docdoku-plm-server-py/tests/test_document_service.py
git commit -m "feat(py): document_service——CRUD+签出签入+发布废弃+文件夹+模板"
```

---

## Task 3: 文档端点（`app/routers/documents.py`）

**Files:**
- Create: `docdoku-plm-server-py/app/routers/documents.py`
- Modify: `docdoku-plm-server-py/app/main.py`
- Test: `docdoku-plm-server-py/tests/test_documents_api.py`

- [ ] **Step 1: 写集成测试**

```python
# tests/test_documents_api.py
from fastapi.testclient import TestClient
from app.main import app
PREFIX = "/docdoku-plm-server-rest/api"
WS = "Workspace_2"
client = TestClient(app)


def _token():
    r = client.post(f"{PREFIX}/auth/login",
                    json={"login": "test1", "password": "password"})
    return r.headers.get("jwt")


def _cleanup(h, doc_id):
    client.put(f"{PREFIX}/workspaces/{WS}/documents/{doc_id}-A/checkin", headers=h)
    client.request("DELETE",
                   f"{PREFIX}/workspaces/{WS}/documents/{doc_id}-A", headers=h)


def test_create_and_delete():
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    doc_id = "P2API-1"
    resp = client.post(f"{PREFIX}/workspaces/{WS}/documents",
                       json={"reference": doc_id, "title": "Test"}, headers=h)
    assert resp.status_code == 201
    _cleanup(h, doc_id)
```

- [ ] **Step 2: 运行→FAIL→实现端点→PASS→Commit**

```bash
git add docdoku-plm-server-py/app/routers/documents.py docdoku-plm-server-py/app/main.py docdoku-plm-server-py/tests/test_documents_api.py
git commit -m "feat(py): 文档端点——documents CRUD+签出签入+状态+标签+搜索"
```

---

## Task 4: 文档文件端点（`app/routers/document_files.py`）

**Files:**
- Create: `docdoku-plm-server-py/app/routers/document_files.py` + `tests/test_document_files_api.py`
- Modify: `app/main.py`

**端点**：
- `POST /api/files/{ws}/documents/{id}/{version}/{iteration}` — multipart, field=upload。校验签出状态→`NotAllowedException4`
- `GET /api/files/{ws}/documents/{id}/{version}/{iteration}/{fileName}` — 下载

- [ ] **Step 1: TDD→PASS→Commit**

```bash
git commit -m "feat(py): 文档文件上传下载端点"
```

---

## Task 5: 文件夹端点（`app/routers/folders.py`）

**Files:**
- Create: `docdoku-plm-server-py/app/routers/folders.py` + `tests/test_folders_api.py`
- Modify: `app/main.py`

**注意**：folder 路由用 `{folder_path:path}` 捕获含 `/` 的路径。DELETE 拒绝非空文件夹（子文件夹>0→403）。

- [ ] **Step 1: TDD→PASS→Commit**

```bash
git commit -m "feat(py): 文件夹端点——list/create/rename/delete"
```

---

## Task 6: 文档模板端点（`app/routers/document_templates.py`）

**Files:**
- Create: `docdoku-plm-server-py/app/routers/document_templates.py` + `tests/test_document_templates_api.py`
- Modify: `app/main.py`

- [ ] **Step 1: TDD→PASS→Commit**

```bash
git commit -m "feat(py): 文档模板端点——CRUD+文件上传下载"
```

---

## Task 7: 对齐审计 + Payara 对拍 + 切 Nginx

**Files:**
- Modify: `docdoku-plm-docker/front/nginx.conf`

**Nginx 新增**（在兜底 Payara 之前）：

```nginx
location ~ ^/docdoku-plm-server-rest/api/workspaces/[^/]+/documents {
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

location ~ ^/docdoku-plm-server-rest/api/workspaces/[^/]+/folders {
    set $backpy "back-py:8000";
    proxy_pass http://$backpy;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
}

location ~ ^/docdoku-plm-server-rest/api/workspaces/[^/]+/document-templates {
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

location ~ ^/docdoku-plm-server-rest/api/files/[^/]+/documents {
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

- [ ] **Step 1: 全量测试 + 重建 back-py**
- [ ] **Step 2: Payara 对拍关键端点**（文档列表/详情/删除）
- [ ] **Step 3: 通过后切 Nginx + 重启 front**
- [ ] **Step 4: 更新 CHANGELOG/REMINDERS/路线图**

```bash
git add docdoku-plm-docker/front/nginx.conf docs/CHANGELOG.md docs/REMINDERS.md
git commit -m "feat(py): P2 文档/文件夹/模板 Nginx 切换+文档更新"
```

---

## 前端实测清单（交用户验收）

1. 创建文档 → 出现在列表
2. 签出 → 上传文件 → 下载文件
3. 签入 → release → RELEASED → obsolete → OBSOLETE
4. newVersion → 新版本出现
5. 打标签 → 搜文档
6. 创建文件夹 → 子文件夹 → 删除文件夹
7. 创建模板 → 删除模板

---

## Self-Review 结果

- **Spec 覆盖**：文档 CRUD（Task 2/3）✅；文件上传下载（Task 4）✅；文件夹（Task 5）✅；模板（Task 6）✅；对齐审计+对拍+Nginx（Task 7）✅。
- **Placeholder 扫描**：无 TBD/TODO。
- **类型一致**：DocumentService 所有方法签名全计划一致。checkout 的 `NotAllowedException72`（非最新版）需跨版本比较当前版本是否为最新——计划中暂略，审计阶段补齐。
