"""变更模块共享工具函数—— _item_to_dict, _get_acl_dict, _get_user_name 等。"""
from typing import Optional
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session
from app.models.auth import Account
from app.models.change import ChangeIssue, ChangeRequest, ChangeOrder
from app.models.security import AclUserEntry, AclUserGroupEntry
from app.core.exceptions import AccessRightException
from app.services.acl_helper import check_write_access, check_read_access

_NAME_CACHE: dict = {}

_PRIORITY_NAMES = {0: "LOW", 1: "MEDIUM", 2: "HIGH", 3: "EMERGENCY"}
_CATEGORY_NAMES = {0: "ADAPTIVE", 1: "CORRECTIVE", 2: "PERFECTIVE", 3: "PREVENTIVE", 4: "OTHER"}
_PERMISSION_NAMES = {0: "FORBIDDEN", 1: "READ_ONLY", 2: "FULL_ACCESS"}


def _get_user_name(db: Session, login: str) -> str:
    if not login:
        return ""
    key = login
    if key in _NAME_CACHE:
        return _NAME_CACHE[key]
    acc = db.query(Account).filter(Account.login == login).first()
    name = acc.name if (acc and acc.name) else login
    _NAME_CACHE[key] = name
    return name


def _get_acl_dict(db: Session, acl_id: int | None) -> dict | None:
    if acl_id is None:
        return None
    user_rows = db.query(AclUserEntry).filter(AclUserEntry.acl_id == acl_id).all()
    group_rows = db.query(AclUserGroupEntry).filter(AclUserGroupEntry.acl_id == acl_id).all()
    return {
        "id": acl_id,
        "enabled": True,
        "userEntries": [{"key": r.principal_login, "value": _PERMISSION_NAMES.get(r.permission, "FORBIDDEN")} for r in user_rows],
        "groupEntries": [{"key": r.principal_id, "value": _PERMISSION_NAMES.get(r.permission, "FORBIDDEN")} for r in group_rows],
        "userEntriesMap": {r.principal_login: _PERMISSION_NAMES.get(r.permission, "FORBIDDEN") for r in user_rows},
        "userGroupEntriesMap": {},
    }


def _check_workspace_access(db: Session, ws: str, login: str):
    row = db.execute(sql_text(
        "SELECT 1 FROM userdata WHERE login = :l AND workspace_id = :w"
    ), {"l": login, "w": ws}).first()
    if not row:
        raise AccessRightException("AccessRightException")


def _item_to_dict(item, db: Optional[Session] = None, current_user: Optional[Account] = None) -> dict:
    is_request = isinstance(item, ChangeRequest)
    is_order = isinstance(item, ChangeOrder)
    is_issue = isinstance(item, ChangeIssue)

    author_login = getattr(item, "author_login", "")
    assignee_login = getattr(item, "assignee_login", "")

    author_name = _get_user_name(db, author_login) if db else author_login
    assignee_name = _get_user_name(db, assignee_login) if db else assignee_login

    creation_date = None
    cd = getattr(item, "creation_date", None)
    if cd:
        creation_date = cd.strftime("%Y-%m-%dT%H:%M:%S.") + f"{cd.microsecond // 1000:03d}Z"

    name = getattr(item, "name", getattr(item, "title", ""))

    is_admin = False
    if current_user and db:
        is_admin = db.execute(sql_text(
            "SELECT 1 FROM usergroupmapping WHERE login=:l AND groupname='admin'"
        ), {"l": current_user.login}).first() is not None

    writable = True
    if db and current_user:
        writable = check_write_access(db, getattr(item, "acl_id", None), current_user.login, is_admin)

    data = dict(
        acl=_get_acl_dict(db, getattr(item, "acl_id", None)) or {},
        affectedDocuments=[],
        affectedParts=[],
        assignee=None,
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
                # ACL过滤：只显示当前用户可读的关联问题
                if current_user:
                    issues = [i for i in issues
                              if i.acl_id is None
                              or check_read_access(db, i.acl_id, current_user.login, is_admin)]
                data["addressedChangeIssues"] = [_item_to_dict(i, db, current_user) for i in issues]
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
                # ACL过滤：只显示当前用户可读的关联请求
                if current_user:
                    requests = [r for r in requests
                                if r.acl_id is None
                                or check_read_access(db, r.acl_id, current_user.login, is_admin)]
                data["addressedChangeRequests"] = [_item_to_dict(r, db, current_user) for r in requests]
            else:
                data["addressedChangeRequests"] = []

    return data


def _set_affected_parts(db, ws, item_id, parts_data, table_name, id_column):
    db.execute(sql_text(f"DELETE FROM {table_name} WHERE {id_column}=:iid"),
               {"iid": item_id})
    for part_data in parts_data:
        part_key = part_data.get("partKey", "")
        parts_split = part_key.rsplit("-", 1)
        pn = parts_split[0] if len(parts_split) == 2 else part_key
        ver = parts_split[1] if len(parts_split) == 2 else "A"
        db.execute(sql_text(
            f"INSERT INTO {table_name} ({id_column}, partmaster_workspace_id, "
            f"partmaster_partnumber, partrevision_version, iteration) "
            f"VALUES (:iid, :ws, :pn, :ver, 1)"
        ), {"iid": item_id, "ws": ws, "pn": pn, "ver": ver})
    db.commit()


def _set_affected_documents(db, ws, item_id, docs_data, table_name, id_column):
    db.execute(sql_text(f"DELETE FROM {table_name} WHERE {id_column}=:iid"),
               {"iid": item_id})
    for doc_data in docs_data:
        doc_key = doc_data.get("documentKey", "")
        doc_split = doc_key.rsplit("-", 1)
        dm_id = doc_split[0] if len(doc_split) == 2 else doc_key
        ver = doc_split[1] if len(doc_split) == 2 else "A"
        db.execute(sql_text(
            f"INSERT INTO {table_name} ({id_column}, documentmaster_workspace_id, "
            f"documentmaster_id, documentrevision_version, iteration) "
            f"VALUES (:iid, :ws, :did, :ver, 1)"
        ), {"iid": item_id, "ws": ws, "did": dm_id, "ver": ver})
    db.commit()
