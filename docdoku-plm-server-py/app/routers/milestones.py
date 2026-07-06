"""里程碑（Milestone）端点路由。"""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import AccessRightException
from app.models.auth import Account
from app.models.change import ChangeIssue, ChangeRequest, ChangeOrder, Milestone
from app.models.security import AclUserEntry, AclUserGroupEntry
from app.services.change_manager import ChangeService
from app.services.acl_helper import apply_acl, check_write_access

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
svc = ChangeService()

_NAME_CACHE: dict = {}

_PRIORITY_NAMES = {0: "LOW", 1: "MEDIUM", 2: "HIGH", 3: "EMERGENCY"}
_CATEGORY_NAMES = {0: "ADAPTIVE", 1: "CORRECTIVE", 2: "PERFECTIVE", 3: "PREVENTIVE", 4: "OTHER"}
_PERMISSION_NAMES = {0: "FORBIDDEN", 1: "READ_ONLY", 2: "FULL_ACCESS"}


def _get_acl_dict(db: Session, acl_id: int | None) -> dict | None:
    if acl_id is None:
        return None
    user_rows = db.query(AclUserEntry).filter(AclUserEntry.acl_id == acl_id).all()
    group_rows = db.query(AclUserGroupEntry).filter(AclUserGroupEntry.acl_id == acl_id).all()
    return {
        "id": acl_id,
        "enabled": True,
        "userEntries": {r.principal_login: _PERMISSION_NAMES.get(r.permission, "FORBIDDEN")
                        for r in user_rows},
        "groupEntries": {r.principal_id: _PERMISSION_NAMES.get(r.permission, "FORBIDDEN")
                         for r in group_rows},
    }


def _check_workspace_access(db: Session, ws: str, login: str):
    row = db.execute(sql_text(
        "SELECT 1 FROM userdata WHERE login = :l AND workspace_id = :w"
    ), {"l": login, "w": ws}).first()
    if not row:
        raise AccessRightException("AccessRightException")


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
        acl=_get_acl_dict(db, getattr(item, "acl_id", None)),
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
                data["addressedChangeRequests"] = [_item_to_dict(r, db, current_user) for r in requests]
            else:
                data["addressedChangeRequests"] = []

    return data


def _milestone_to_dict(ms, db: Optional[Session] = None, current_user: Optional[Account] = None) -> dict:
    numberOfOrders = 0
    numberOfRequests = 0
    if db is not None:
        numberOfOrders = db.scalar(sql_text(
            "SELECT COUNT(*) FROM changeorder WHERE milestone_id=:mid"
        ), {"mid": ms.id}) or 0
        numberOfRequests = db.scalar(sql_text(
            "SELECT COUNT(*) FROM changerequest WHERE milestone_id=:mid"
        ), {"mid": ms.id}) or 0

    is_admin = False
    if current_user and db:
        is_admin = db.execute(sql_text(
            "SELECT 1 FROM usergroupmapping WHERE login=:l AND groupname='admin'"
        ), {"l": current_user.login}).first() is not None

    writable = True
    if db and current_user:
        writable = check_write_access(db, getattr(ms, "acl_id", None), current_user.login, is_admin)

    data = dict(
        acl=_get_acl_dict(db, getattr(ms, "acl_id", None)),
        description=getattr(ms, "description", "") or "",
        id=ms.id,
        numberOfOrders=numberOfOrders,
        numberOfRequests=numberOfRequests,
        title=getattr(ms, "title", "") or "",
        workspaceId=getattr(ms, "workspace_id", ""),
        writable=writable,
    )
    dd = getattr(ms, "due_date", None)
    if dd:
        data["dueDate"] = dd.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dd.microsecond // 1000:03d}Z"
    return data


# ── Milestones ──

@router.get("/workspaces/{ws}/changes/milestones")
@router.get("/workspaces/{ws}/changes/milestones/", include_in_schema=False)
def list_milestones(ws: str, current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    return [_milestone_to_dict(m, db, current_user) for m in svc.list_items(db, ws, "milestones")]


@router.post("/workspaces/{ws}/changes/milestones", status_code=201)
@router.post("/workspaces/{ws}/changes/milestones/", status_code=201, include_in_schema=False)
def create_milestone(ws: str, body: dict,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    ms = svc.create_item(db, ws, "milestone", body, current_user.login)
    return _milestone_to_dict(ms, db, current_user)
@router.get("/workspaces/{ws}/changes/milestones/{item_id}")
@router.get("/workspaces/{ws}/changes/milestones/{item_id}/", include_in_schema=False)
def get_milestone(ws: str, item_id: int,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    return _milestone_to_dict(svc.get_by_id(db, Milestone, ws, item_id), db, current_user)

@router.put("/workspaces/{ws}/changes/milestones/{item_id}")
@router.put("/workspaces/{ws}/changes/milestones/{item_id}/", include_in_schema=False)
def update_milestone(ws: str, item_id: int, body: dict,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    return _milestone_to_dict(svc.update_item(db, ws, "milestone", item_id, body), db, current_user)


@router.delete("/workspaces/{ws}/changes/milestones/{item_id}", status_code=204)
@router.delete("/workspaces/{ws}/changes/milestones/{item_id}/", status_code=204, include_in_schema=False)
def delete_milestone(ws: str, item_id: int,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    svc.delete_item(db, Milestone, ws, item_id)


@router.get("/workspaces/{ws}/changes/milestones/{milestone_id}/requests")
@router.get("/workspaces/{ws}/changes/milestones/{milestone_id}/requests/", include_in_schema=False)
def get_milestone_requests(ws: str, milestone_id: int,
                           current_user: Account = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    items = db.query(ChangeRequest).filter(
        ChangeRequest.workspace_id == ws,
        ChangeRequest.milestone_id == milestone_id
    ).all()
    return [_item_to_dict(r, db, current_user) for r in items]


@router.get("/workspaces/{ws}/changes/milestones/{milestone_id}/orders")
@router.get("/workspaces/{ws}/changes/milestones/{milestone_id}/orders/", include_in_schema=False)
def get_milestone_orders(ws: str, milestone_id: int,
                         current_user: Account = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    items = db.query(ChangeOrder).filter(
        ChangeOrder.workspace_id == ws,
        ChangeOrder.milestone_id == milestone_id
    ).all()
    return [_item_to_dict(o, db, current_user) for o in items]


@router.put("/workspaces/{ws}/changes/milestones/{milestone_id}/acl")
@router.put("/workspaces/{ws}/changes/milestones/{milestone_id}/acl/", include_in_schema=False)
def set_milestone_acl(ws: str, milestone_id: int, body: dict,
                      current_user: Account = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    item = svc.get_by_id(db, Milestone, ws, milestone_id)
    new_acl_id = apply_acl(db, item.acl_id,
                           body.get("userEntries", {}),
                           body.get("groupEntries", {}))
    item.acl_id = new_acl_id
    db.commit()
    return {"aclId": new_acl_id}
