from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session
from app.models.change import (
    ChangeIssue, ChangeRequest, ChangeOrder, Milestone,
    change_issue_tags, change_request_tags, change_order_tags,
)

TYPE_MAP = {
    "issue": ChangeIssue, "issues": ChangeIssue,
    "request": ChangeRequest, "requests": ChangeRequest,
    "order": ChangeOrder, "orders": ChangeOrder,
    "milestone": Milestone, "milestones": Milestone,
}

TAG_TABLES = {
    ChangeIssue: change_issue_tags,
    ChangeRequest: change_request_tags,
    ChangeOrder: change_order_tags,
}


class ChangeService:

    def _cls(self, type_name: str):
        cls = TYPE_MAP.get(type_name)
        if cls is None:
            raise HTTPException(400, f"Unknown change type: {type_name}")
        return cls

    def list_items(self, db: Session, ws: str, type_name: str):
        cls = self._cls(type_name)
        return db.query(cls).filter(cls.workspace_id == ws).all()

    def get_by_id(self, db: Session, cls, ws: str, item_id: int):
        item = db.query(cls).filter(
            cls.workspace_id == ws, cls.id == item_id).first()
        if item is None:
            raise HTTPException(404, f"{cls.__name__} not found")
        return item

    def create_item(self, db: Session, ws: str, type_name: str,
                    body: dict, user_login: str):
        cls = self._cls(type_name)
        now = datetime.utcnow()
        kwargs = dict(workspace_id=ws)
        if hasattr(cls, "creation_date"):
            kwargs["creation_date"] = now
        if hasattr(cls, "author_workspace_id"):
            kwargs["author_workspace_id"] = ws
        if hasattr(cls, "author_login"):
            kwargs["author_login"] = user_login
        for field in ("name", "description", "priority", "category",
                      "initiator", "milestone_id", "title"):
            if field in body:
                kwargs[field] = body[field]
        if "assignee" in body and isinstance(body["assignee"], dict):
            kwargs["assignee_login"] = body["assignee"].get("login")
        if "dueDate" in body:
            kwargs["due_date"] = body["dueDate"]
        item = cls(**kwargs)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def update_item(self, db: Session, ws: str, type_name: str,
                    item_id: int, body: dict):
        cls = self._cls(type_name)
        item = self.get_by_id(db, cls, ws, item_id)
        for key, val in body.items():
            if key == "assignee" and isinstance(val, dict):
                item.assignee_login = val.get("login")
            elif key == "dueDate":
                item.due_date = val
            elif hasattr(item, key):
                setattr(item, key, val)
        db.commit()
        db.refresh(item)
        return item

    def delete_item(self, db: Session, cls, ws: str, item_id: int):
        item = self.get_by_id(db, cls, ws, item_id)
        # 清理受影响关联（通过原始 SQL 写入的关联，ORM 不感知）
        prefix_map = {
            ChangeIssue: "changeissue",
            ChangeOrder: "changeorder",
            ChangeRequest: "changereq",
        }
        prefix = prefix_map.get(cls, "")
        if prefix:
            for suffix in ("_affected_part", "_affected_document"):
                db.execute(sql_text(
                    f"DELETE FROM {prefix}{suffix} "
                    f"WHERE {prefix}_id=:iid"
                ), {"iid": item_id})
        # 清理 tags 关联（FK 约束需要先清关联再删记录）
        tag_tbl = TAG_TABLES.get(cls)
        if tag_tbl is not None:
            pk_col = list(tag_tbl.primary_key.columns)[0]
            db.execute(tag_tbl.delete().where(pk_col == item_id))
        # 清理跨类型关联
        if cls is ChangeRequest:
            db.execute(sql_text(
                "DELETE FROM changerequest_changeissue WHERE changerequest_id=:iid"
            ), {"iid": item_id})
            db.execute(sql_text(
                "DELETE FROM changeorder_changerequest WHERE changerequest_id=:iid"
            ), {"iid": item_id})
        elif cls is ChangeOrder:
            db.execute(sql_text(
                "DELETE FROM changeorder_changerequest WHERE changeorder_id=:iid"
            ), {"iid": item_id})
        db.delete(item)
        db.commit()

    def _ensure_tag(self, db: Session, ws: str, label: str):
        from app.models.part import Tag
        t = db.query(Tag).filter(
            Tag.workspace_id == ws, Tag.label == label).first()
        if t is None:
            db.add(Tag(workspace_id=ws, label=label))
            db.flush()

    def set_tags(self, db: Session, cls, ws: str, item_id: int, labels: list):
        self.get_by_id(db, cls, ws, item_id)
        tag_tbl = TAG_TABLES[cls]
        pk_col = list(tag_tbl.primary_key.columns)[0]
        db.execute(tag_tbl.delete().where(pk_col == item_id))
        for label in labels:
            self._ensure_tag(db, ws, label)
            db.execute(tag_tbl.insert().values(
                **{pk_col.name: item_id, "tag_workspace_id": ws, "tag_label": label}))
        db.commit()

    def add_tag(self, db: Session, cls, ws: str, item_id: int, label: str):
        self.get_by_id(db, cls, ws, item_id)
        self._ensure_tag(db, ws, label)
        tag_tbl = TAG_TABLES[cls]
        pk_col = list(tag_tbl.primary_key.columns)[0]
        exists = db.execute(tag_tbl.select().where(
            (pk_col == item_id) & (tag_tbl.c.tag_label == label))).first()
        if exists is None:
            db.execute(tag_tbl.insert().values(
                **{pk_col.name: item_id, "tag_workspace_id": ws, "tag_label": label}))
        db.commit()

    def remove_tag(self, db: Session, cls, ws: str, item_id: int, label: str):
        self.get_by_id(db, cls, ws, item_id)
        tag_tbl = TAG_TABLES[cls]
        pk_col = list(tag_tbl.primary_key.columns)[0]
        db.execute(tag_tbl.delete().where(
            (pk_col == item_id) & (tag_tbl.c.tag_label == label)))
        db.commit()
