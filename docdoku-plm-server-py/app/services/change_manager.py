from datetime import datetime
from typing import Optional, Sequence
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session
from app.core.exceptions import (
    AccessRightException, NotAllowedException, EntityConstraintException,
    EntityNotFoundException,
    MilestoneNotFoundException, MilestoneAlreadyExistsException,
    ChangeIssueNotFoundException, ChangeRequestNotFoundException,
    ChangeOrderNotFoundException,
    UserNotFoundException, WrongInputException,
)
from app.models.auth import Account
from app.models.change import (
    ChangeIssue, ChangeRequest, ChangeOrder, Milestone,
    change_issue_tags, change_request_tags, change_order_tags,
)

_NAME_CACHE: dict = {}
_PRIORITY_NAMES = {0: "LOW", 1: "MEDIUM", 2: "HIGH", 3: "EMERGENCY"}
_CATEGORY_NAMES = {0: "ADAPTIVE", 1: "CORRECTIVE", 2: "PERFECTIVE", 3: "PREVENTIVE", 4: "OTHER"}

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
            raise WrongInputException()
        return cls

    def list_items(self, db: Session, ws: str, type_name: str,
                   user_login: str = None, is_admin: bool = False):
        cls = self._cls(type_name)
        items = db.query(cls).filter(cls.workspace_id == ws).all()
        if user_login and not is_admin:
            from app.services.factory.acl_factory import check_read_access
            items = [i for i in items
                     if i.acl_id is None
                     or check_read_access(db, i.acl_id, user_login, is_admin)]
        return items

    def get_by_id(self, db: Session, cls, ws: str, item_id: int):
        item = db.query(cls).filter(
            cls.workspace_id == ws, cls.id == item_id).first()
        if item is None:
            if cls is Milestone:
                raise MilestoneNotFoundException("MilestoneNotFoundException", str(item_id))
            if cls is ChangeIssue:
                raise ChangeIssueNotFoundException("ChangeIssueNotFoundException", str(item_id))
            if cls is ChangeRequest:
                raise ChangeRequestNotFoundException("ChangeRequestNotFoundException", str(item_id))
            if cls is ChangeOrder:
                raise ChangeOrderNotFoundException("ChangeOrderNotFoundException", str(item_id))
            raise EntityNotFoundException("EntityNotFoundException", cls.__name__)
        return item

    def _check_assignee(self, db: Session, ws: str, assignee_login: str):
        if assignee_login:
            acc = db.query(Account).filter(Account.login == assignee_login).first()
            if not acc:
                raise NotAllowedException("NotAllowedException71")
            if not acc.enabled:
                raise NotAllowedException("NotAllowedException71")
            # 检查用户在 workspace 中是否已启用 (Java isUserEnabled)
            # 直接成员
            member = db.execute(sql_text(
                "SELECT 1 FROM workspaceusermembership "
                "WHERE workspace_id = :ws AND member_login = :login"
            ), {"ws": ws, "login": assignee_login}).first()
            # 通过组的成员（Java 同时检查 workspaceusergroupmembership）
            group_member = db.execute(sql_text(
                "SELECT 1 FROM workspaceusergroupmembership wgm "
                "JOIN usergroupmapping m ON m.groupname = wgm.member_id "
                "WHERE wgm.workspace_id = :ws AND m.login = :login"
            ), {"ws": ws, "login": assignee_login}).first()
            if not member and not group_member:
                raise NotAllowedException("NotAllowedException71")

    def create_item(self, db: Session, ws: str, type_name: str,
                    body: dict, user_login: str):
        cls = self._cls(type_name)
        now = datetime.utcnow()
        # 验证 milestoneId：创建 Request/Order 时 milestone 必须存在
        # Java ChangeOrderDTO/ChangeRequestDTO 字段名是 milestoneId（驼峰）
        milestone_id_val = body.get("milestoneId")
        if cls in (ChangeRequest, ChangeOrder) and milestone_id_val:
            ms = db.query(Milestone).filter(
                Milestone.id == milestone_id_val,
                Milestone.workspace_id == ws,
            ).first()
            if not ms:
                raise MilestoneNotFoundException(
                    "MilestoneNotFoundException", str(milestone_id_val))
        # 验证 initiator：创建 Issue 时 initiator 必须是有效用户
        if cls is ChangeIssue and body.get("initiator"):
            acc = db.query(Account).filter(Account.login == body["initiator"]).first()
            if not acc:
                raise UserNotFoundException("UserNotFoundException", body["initiator"])
        if cls is Milestone:
            existing = db.query(Milestone).filter(
                Milestone.workspace_id == ws,
                Milestone.title == body.get("title"),
            ).first()
            if existing:
                raise MilestoneAlreadyExistsException(
                    "MilestoneAlreadyExistsException", body.get("title", ""))
        kwargs = dict(workspace_id=ws)
        if hasattr(cls, "creation_date"):
            kwargs["creation_date"] = now
        if hasattr(cls, "author_workspace_id"):
            kwargs["author_workspace_id"] = ws
        if hasattr(cls, "author_login"):
            kwargs["author_login"] = user_login
        for field in ("name", "description", "priority", "category",
                       "initiator", "title"):
            if field in body:
                kwargs[field] = body[field]
        # milestoneId（驼峰）→ ORM milestone_id（蛇形）
        if "milestoneId" in body and body["milestoneId"] is not None:
            kwargs["milestone_id"] = body["milestoneId"]
        if "assignee" in body and isinstance(body["assignee"], dict):
            assignee_login = body["assignee"].get("login")
            self._check_assignee(db, ws, assignee_login)
            kwargs["assignee_login"] = assignee_login
        if "dueDate" in body:
            kwargs["due_date"] = body["dueDate"]
        # workspace 写权限检查（对齐 Java checkWorkspaceWriteAccess）
        from app.services.factory.acl_factory import check_write_access
        if not check_write_access(db, None, user_login, False, workspace_id=ws):
            raise AccessRightException("AccessRightException", user_login)
        item = cls(**kwargs)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def update_item(self, db: Session, ws: str, type_name: str,
                    item_id: int, body: dict,
                    user_login: str | None = None,
                    is_admin: bool = False):
        cls = self._cls(type_name)
        item = self.get_by_id(db, cls, ws, item_id)
        # checkChangeItemWriteAccess（对齐 Java）
        from app.services.factory.acl_factory import check_write_access
        acl_id = getattr(item, "acl_id", None)
        if not check_write_access(db, acl_id, user_login, is_admin, workspace_id=ws):
            raise AccessRightException("AccessRightException", user_login)

        # 对齐 Java updateChangeIssue/updateChangeRequest/updateChangeOrder:
        # 仅应用白名单可变字段（description, priority, category, assignee, milestone_id），
        # 对 name/id/author/initiator 等非白名单字段【静默忽略】——因 Java REST 层
        # 接收完整 DTO 但只提取 description/priority/assignee/category，且前端 save 会带
        # author/initiator，抛错会破坏前端编辑弹框。故此处不抛异常，只忽略。
        for key, val in body.items():
            if key == "assignee" and isinstance(val, dict):
                assignee_login = val.get("login")
                self._check_assignee(db, ws, assignee_login)
                item.assignee_login = assignee_login
            elif key == "dueDate":
                item.due_date = val
            elif key == "milestoneId" and cls in (ChangeRequest, ChangeOrder):
                # Java ChangeOrderDTO/ChangeRequestDTO 字段名是 milestoneId（驼峰）
                ms = db.query(Milestone).filter(
                    Milestone.id == val,
                    Milestone.workspace_id == ws,
                ).first()
                if not ms:
                    raise MilestoneNotFoundException(
                        "MilestoneNotFoundException", str(val))
                item.milestone_id = val  # ORM 列名是蛇形
            elif key in ("description", "priority", "category"):
                setattr(item, key, val)
            # Milestone 额外支持 title（非 change item 的标准字段）
            elif cls is Milestone and key in ("title",):
                setattr(item, key, val)
            # 其余字段（name/id/author/author_login/workspace_id/creation_date/
            # acl/tags/initiator 及未知字段）静默忽略，对齐 Java DTO 提取行为
        db.commit()
        db.refresh(item)
        return item

    def delete_item(self, db: Session, cls, ws: str, item_id: int,
                    user_login: str = None, is_admin: bool = False):
        item = self.get_by_id(db, cls, ws, item_id)
        # ACL 写权限检查（对齐 Java checkChangeItemWriteAccess）
        if user_login and not is_admin:
            acl_id = getattr(item, "acl_id", None)
            if acl_id is not None:
                from app.services.factory.acl_factory import check_write_access
                if not check_write_access(db, acl_id, user_login, False, workspace_id=ws):
                    raise AccessRightException("AccessRightException", user_login)
            else:
                # ACL 为 null → 需要 workspace 写权限（对齐 Java hasWorkspaceWriteAccess）
                has_write = db.execute(sql_text(
                    "SELECT 1 FROM workspaceusermembership "
                    "WHERE workspace_id=:ws AND member_login=:l AND readonly=false"
                ), {"ws": ws, "l": user_login}).first()
                if not has_write:
                    has_write = db.execute(sql_text(
                        "SELECT 1 FROM workspaceusergroupmembership wgm "
                        "JOIN usergroupmapping m ON m.groupname = wgm.member_id "
                        "WHERE wgm.workspace_id=:ws AND m.login=:l AND wgm.readonly=false"
                    ), {"ws": ws, "l": user_login}).first()
                if not has_write:
                    raise AccessRightException("AccessRightException", user_login)
        # 里程碑删除前检查约束
        if cls is Milestone:
            orders = db.query(ChangeOrder).filter(
                ChangeOrder.milestone_id == item_id,
                ChangeOrder.workspace_id == ws,
            ).count()
            requests = db.query(ChangeRequest).filter(
                ChangeRequest.milestone_id == item_id,
                ChangeRequest.workspace_id == ws,
            ).count()
            if orders > 0:
                raise EntityConstraintException("EntityConstraintException8")
            if requests > 0:
                raise EntityConstraintException("EntityConstraintException9")
        # Issue 删除前检查是否已被 ChangeRequest 引用
        if cls is ChangeIssue:
            linked = db.scalar(sql_text(
                "SELECT COUNT(*) FROM changerequest_changeissue "
                "WHERE changeissue_id=:iid"
            ), {"iid": item_id}) or 0
            if linked > 0:
                raise EntityConstraintException("EntityConstraintException26")
        # Request 删除前检查是否已被 ChangeOrder 引用
        if cls is ChangeRequest:
            linked = db.scalar(sql_text(
                "SELECT COUNT(*) FROM changeorder_changerequest "
                "WHERE changerequest_id=:iid"
            ), {"iid": item_id}) or 0
            if linked > 0:
                raise EntityConstraintException("EntityConstraintException10")
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

    def set_tags(self, db: Session, cls, ws: str, item_id: int, labels: list,
                 user_login: str | None = None,
                 is_admin: bool = False):
        self.get_by_id(db, cls, ws, item_id)
        # checkChangeItemWriteAccess（对齐 Java）
        from app.services.factory.acl_factory import check_write_access
        item = self.get_by_id(db, cls, ws, item_id)
        acl_id = getattr(item, "acl_id", None)
        if not check_write_access(db, acl_id, user_login, is_admin, workspace_id=ws):
            raise AccessRightException("AccessRightException", user_login)
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

    # ========== 从 change_common 迁入的 DB 操作 ==========

    def get_user_name(self, db: Session, login: str) -> str:
        if not login:
            return ""
        key = login
        if key in _NAME_CACHE:
            return _NAME_CACHE[key]
        acc = db.query(Account).filter(Account.login == login).first()
        name = acc.name if (acc and acc.name) else login
        _NAME_CACHE[key] = name
        return name

    def is_admin(self, db: Session, login: str) -> bool:
        return db.execute(sql_text(
            "SELECT 1 FROM usergroupmapping WHERE login=:l AND groupname='admin'"
        ), {"l": login}).first() is not None

    def build_item_dto(self, item, db: Optional[Session] = None,
                       current_user: Optional[Account] = None) -> dict:
        """构建变更项完整 DTO（含 affected parts/docs、关联 issues/requests）"""
        from app.services.factory.acl_factory import check_write_access, check_read_access, build_acl_dict
        from app.models.util.date_utils import format_iso_date

        is_request = isinstance(item, ChangeRequest)
        is_order = isinstance(item, ChangeOrder)
        is_issue = isinstance(item, ChangeIssue)

        author_login = getattr(item, "author_login", "")
        assignee_login = getattr(item, "assignee_login", "")

        author_name = self.get_user_name(db, author_login) if db else author_login
        assignee_name = self.get_user_name(db, assignee_login) if db else assignee_login

        creation_date = None
        cd = getattr(item, "creation_date", None)
        if cd:
            creation_date = format_iso_date(cd)

        name = getattr(item, "name", getattr(item, "title", ""))

        is_admin = False
        if current_user and db:
            is_admin = self.is_admin(db, current_user.login)

        writable = True
        if db and current_user:
            writable = check_write_access(db, getattr(item, "acl_id", None),
                                          current_user.login, is_admin,
                                          workspace_id=getattr(item, "workspace_id", None))

        data = dict(
            acl=build_acl_dict(db, getattr(item, "acl_id", None), include_id=True) or {},
            affectedDocuments=[],
            affectedParts=[],
            assignee=assignee_login or None,
            assigneeName=assignee_name or None,
            author=author_login,
            authorName=author_name or author_login,
            category=_CATEGORY_NAMES.get(getattr(item, "category", None)),
            creationDate=creation_date,
            description=getattr(item, "description", "") or "",
            id=item.id,
            name=name,
            priority=_PRIORITY_NAMES.get(getattr(item, "priority", None)),
            tags=[t.label for t in (getattr(item, "tags", None) or [])],
            workspaceId=getattr(item, "workspace_id", ""),
            writable=writable,
        )

        if is_issue:
            data["initiator"] = getattr(item, "initiator", None)

        if is_request:
            data["milestoneId"] = getattr(item, "milestone_id", None) or -1
        elif is_order:
            data["milestoneId"] = getattr(item, "milestone_id", None) or -1

        if db:
            prefix_map = {
                ChangeIssue: ("changeissue", "changeissue_id"),
                ChangeOrder: ("changeorder", "changeorder_id"),
                ChangeRequest: ("changereq", "changerequest_id"),
            }
            prefix, id_col = prefix_map.get(type(item), ("", ""))
            if prefix:
                rows = db.execute(sql_text(
                    f"SELECT partmaster_partnumber, partrevision_version "
                    f"FROM {prefix}_affected_part WHERE {id_col}=:iid"
                ), {"iid": item.id}).fetchall()
                data["affectedParts"] = [
                    {"partKey": f"{r[0]}-{r[1]}", "partNumber": r[0], "version": r[1]}
                    for r in rows
                ]
                rows = db.execute(sql_text(
                    f"SELECT documentmaster_id, documentrevision_version "
                    f"FROM {prefix}_affected_document WHERE {id_col}=:iid"
                ), {"iid": item.id}).fetchall()
                data["affectedDocuments"] = [
                    {"documentKey": f"{r[0]}-{r[1]}", "documentMasterId": r[0], "version": r[1]}
                    for r in rows
                ]
            if is_request:
                issue_ids = db.execute(sql_text(
                    "SELECT changeissue_id FROM changerequest_changeissue "
                    "WHERE changerequest_id=:iid"
                ), {"iid": item.id}).fetchall()
                if issue_ids:
                    issues = db.query(ChangeIssue).filter(
                        ChangeIssue.id.in_([r[0] for r in issue_ids])
                    ).all()
                    if current_user:
                        issues = [i for i in issues
                                  if i.acl_id is None
                                  or check_read_access(db, i.acl_id, current_user.login, is_admin)]
                    data["addressedChangeIssues"] = [self.build_item_dto(i, db, current_user) for i in issues]
                else:
                    data["addressedChangeIssues"] = []
            elif is_order:
                req_ids = db.execute(sql_text(
                    "SELECT changerequest_id FROM changeorder_changerequest "
                    "WHERE changeorder_id=:iid"
                ), {"iid": item.id}).fetchall()
                if req_ids:
                    requests = db.query(ChangeRequest).filter(
                        ChangeRequest.id.in_([r[0] for r in req_ids])
                    ).all()
                    if current_user:
                        requests = [r for r in requests
                                    if r.acl_id is None
                                    or check_read_access(db, r.acl_id, current_user.login, is_admin)]
                    data["addressedChangeRequests"] = [self.build_item_dto(r, db, current_user) for r in requests]
                else:
                    data["addressedChangeRequests"] = []

        return data

    def set_affected_parts(self, db: Session, ws: str, item_id: int,
                           parts_data: Sequence[dict], table_name: str, id_column: str,
                           user_login: str | None = None, is_admin: bool = False):
        from app.services.factory.acl_factory import check_write_access
        if user_login:
            item_table = id_column.replace("_id", "")
            acl_id = db.scalar(sql_text(
                f"SELECT acl_id FROM {item_table} WHERE id = :iid"
            ), {"iid": item_id})
            has_access = check_write_access(db, acl_id, user_login, is_admin, workspace_id=ws)
            if not has_access:
                raise AccessRightException("AccessRightException", user_login)
        db.execute(sql_text(f"DELETE FROM {table_name} WHERE {id_column}=:iid"),
                   {"iid": item_id})
        for part_data in parts_data:
            part_key = part_data.get("partKey", "")
            parts_split = part_key.rsplit("-", 1)
            pn = parts_split[0] if len(parts_split) == 2 else part_key
            ver = parts_split[1] if len(parts_split) == 2 else "A"
            iteration = part_data.get("iteration")
            if iteration is None:
                iteration = db.scalar(sql_text(
                    "SELECT MAX(iteration) FROM partiteration "
                    "WHERE partmaster_partnumber = :pn "
                    "AND partrevision_version = :ver "
                    "AND workspace_id = :ws"
                ), {"pn": pn, "ver": ver, "ws": ws}) or 1
            db.execute(sql_text(
                f"INSERT INTO {table_name} ({id_column}, partmaster_workspace_id, "
                f"partmaster_partnumber, partrevision_version, iteration) "
                f"VALUES (:iid, :ws, :pn, :ver, :iter)"
            ), {"iid": item_id, "ws": ws, "pn": pn, "ver": ver, "iter": iteration})
        db.commit()

    def set_affected_documents(self, db: Session, ws: str, item_id: int,
                               docs_data: Sequence[dict], table_name: str, id_column: str,
                               user_login: str | None = None, is_admin: bool = False):
        from app.services.factory.acl_factory import check_write_access
        if user_login:
            item_table = id_column.replace("_id", "")
            acl_id = db.scalar(sql_text(
                f"SELECT acl_id FROM {item_table} WHERE id = :iid"
            ), {"iid": item_id})
            has_access = check_write_access(db, acl_id, user_login, is_admin, workspace_id=ws)
            if not has_access:
                raise AccessRightException("AccessRightException", user_login)
        db.execute(sql_text(f"DELETE FROM {table_name} WHERE {id_column}=:iid"),
                   {"iid": item_id})
        for doc_data in docs_data:
            doc_key = doc_data.get("documentKey", "")
            doc_split = doc_key.rsplit("-", 1)
            dm_id = doc_split[0] if len(doc_split) == 2 else doc_key
            ver = doc_split[1] if len(doc_split) == 2 else "A"
            iteration = doc_data.get("iteration")
            if iteration is None:
                iteration = db.scalar(sql_text(
                    "SELECT MAX(iteration) FROM documentiteration "
                    "WHERE documentmaster_id = :did "
                    "AND documentrevision_version = :ver "
                    "AND workspace_id = :ws"
                ), {"did": dm_id, "ver": ver, "ws": ws}) or 1
            db.execute(sql_text(
                f"INSERT INTO {table_name} ({id_column}, documentmaster_workspace_id, "
                f"documentmaster_id, documentrevision_version, iteration) "
                f"VALUES (:iid, :ws, :did, :ver, :iter)"
            ), {"iid": item_id, "ws": ws, "did": dm_id, "ver": ver, "iter": iteration})
        db.commit()

    def set_order_affected_requests(self, db: Session, ws: str, item_id: int,
                                     requests_data: Sequence[dict]):
        db.execute(sql_text(
            "DELETE FROM changeorder_changerequest WHERE changeorder_id=:iid"
        ), {"iid": item_id})
        for req_data in requests_data:
            req_id = req_data.get("id") if isinstance(req_data, dict) else req_data
            if req_id:
                db.execute(sql_text(
                    "INSERT INTO changeorder_changerequest (changeorder_id, changerequest_id) "
                    "VALUES (:oid, :rid)"
                ), {"oid": item_id, "rid": req_id})
        db.commit()

    def set_request_affected_issues(self, db: Session, ws: str, item_id: int,
                                     issues_data: Sequence[dict]):
        db.execute(sql_text(
            "DELETE FROM changerequest_changeissue WHERE changerequest_id=:iid"
        ), {"iid": item_id})
        for issue_data in issues_data:
            issue_id = issue_data.get("id") if isinstance(issue_data, dict) else issue_data
            if issue_id:
                db.execute(sql_text(
                    "INSERT INTO changerequest_changeissue (changerequest_id, changeissue_id) "
                    "VALUES (:rid, :iid)"
                ), {"rid": item_id, "iid": issue_id})
        db.commit()

    def get_milestone_counts(self, db: Session, milestone_id: int) -> tuple:
        """返回 (numberOfOrders, numberOfRequests)"""
        numberOfOrders = db.scalar(sql_text(
            "SELECT COUNT(*) FROM changeorder WHERE milestone_id=:mid"
        ), {"mid": milestone_id}) or 0
        numberOfRequests = db.scalar(sql_text(
            "SELECT COUNT(*) FROM changerequest WHERE milestone_id=:mid"
        ), {"mid": milestone_id}) or 0
        return numberOfOrders, numberOfRequests
