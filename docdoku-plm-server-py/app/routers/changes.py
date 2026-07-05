"""变更管理端点路由（ChangeIssues/ChangeRequests/ChangeOrders/Milestones）。"""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.models.change import ChangeIssue, ChangeRequest, ChangeOrder, Milestone
from app.services.change_service import ChangeService

router = APIRouter()
svc = ChangeService()

_NAME_CACHE: dict = {}

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


def _item_to_dict(item, db: Optional[Session] = None) -> dict:
    is_request = isinstance(item, ChangeRequest)
    is_order = isinstance(item, ChangeOrder)

    author_login = getattr(item, "author_login", "")
    assignee_login = getattr(item, "assignee_login", "")

    author_name = _get_user_name(db, author_login) if db else author_login
    assignee_name = _get_user_name(db, assignee_login) if db else assignee_login

    creation_date = None
    cd = getattr(item, "creation_date", None)
    if cd:
        creation_date = cd.strftime("%Y-%m-%dT%H:%M:%S.") + f"{cd.microsecond // 1000:03d}Z"

    name = getattr(item, "name", getattr(item, "title", ""))

    data = dict(
        acl=None,
        affectedDocuments=[],
        affectedParts=[],
        assignee=None,
        assigneeName=assignee_name or None,
        author=author_login,
        authorName=author_name or author_login,
        creationDate=creation_date,
        description=getattr(item, "description", "") or "",
        id=item.id,
        name=name,
        tags=[t.label for t in (getattr(item, "tags", None) or [])],
        workspaceId=getattr(item, "workspace_id", ""),
        writable=True,
    )

    if is_request:
        data["addressedChangeIssues"] = []
        data["milestoneId"] = getattr(item, "milestone_id", None) or -1
    elif is_order:
        data["addressedChangeRequests"] = []
        data["milestoneId"] = getattr(item, "milestone_id", None) or -1

    return data


def _milestone_to_dict(ms, db: Optional[Session] = None) -> dict:
    data = dict(
        description=getattr(ms, "description", "") or "",
        id=ms.id,
        numberOfOrders=0,
        numberOfRequests=0,
        title=getattr(ms, "title", "") or "",
        workspaceId=getattr(ms, "workspace_id", ""),
        writable=True,
    )
    dd = getattr(ms, "due_date", None)
    if dd:
        data["dueDate"] = dd.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dd.microsecond // 1000:03d}Z"
    return data


# ── Issues ──

@router.get("/workspaces/{ws}/changes/issues")
def list_issues(ws: str, current_user: Account = Depends(get_current_user),
                db: Session = Depends(get_db)):
    return [_item_to_dict(i, db) for i in svc.list_items(db, ws, "issues")]


@router.post("/workspaces/{ws}/changes/issues", status_code=201)
@router.post("/workspaces/{ws}/changes/issues/", status_code=201, include_in_schema=False)
def create_issue(ws: str, body: dict,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    it = svc.create_item(db, ws, "issue", body, current_user.login)
    return _item_to_dict(it, db)


@router.get("/workspaces/{ws}/changes/issues/{item_id}")
def get_issue(ws: str, item_id: int,
              current_user: Account = Depends(get_current_user),
              db: Session = Depends(get_db)):
    return _item_to_dict(svc.get_by_id(db, ChangeIssue, ws, item_id), db)


@router.put("/workspaces/{ws}/changes/issues/{item_id}")
def update_issue(ws: str, item_id: int, body: dict,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    return _item_to_dict(svc.update_item(db, ws, "issue", item_id, body), db)


@router.delete("/workspaces/{ws}/changes/issues/{item_id}", status_code=204)
def delete_issue(ws: str, item_id: int,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    svc.delete_item(db, ChangeIssue, ws, item_id)


@router.put("/workspaces/{ws}/changes/issues/{item_id}/tags")
def set_issue_tags(ws: str, item_id: int, body: dict,
                   current_user: Account = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    svc.set_tags(db, ChangeIssue, ws, item_id, body.get("tags", []))
    it = svc.get_by_id(db, ChangeIssue, ws, item_id)
    return _item_to_dict(it, db)


@router.post("/workspaces/{ws}/changes/issues/{item_id}/tags")
def add_issue_tag(ws: str, item_id: int, body: dict,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    svc.add_tag(db, ChangeIssue, ws, item_id, body.get("tag", ""))
    it = svc.get_by_id(db, ChangeIssue, ws, item_id)
    return _item_to_dict(it, db)


@router.delete("/workspaces/{ws}/changes/issues/{item_id}/tags/{tag_label}")
def remove_issue_tag(ws: str, item_id: int, tag_label: str,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    svc.remove_tag(db, ChangeIssue, ws, item_id, tag_label)
    it = svc.get_by_id(db, ChangeIssue, ws, item_id)
    return _item_to_dict(it, db)


# ── Requests ──

@router.get("/workspaces/{ws}/changes/requests")
def list_requests(ws: str, current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    return [_item_to_dict(r, db) for r in svc.list_items(db, ws, "requests")]


@router.post("/workspaces/{ws}/changes/requests", status_code=201)
@router.post("/workspaces/{ws}/changes/requests/", status_code=201, include_in_schema=False)
def create_request(ws: str, body: dict,
                   current_user: Account = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    it = svc.create_item(db, ws, "request", body, current_user.login)
    return _item_to_dict(it, db)


@router.get("/workspaces/{ws}/changes/requests/{item_id}")
def get_request(ws: str, item_id: int,
                current_user: Account = Depends(get_current_user),
                db: Session = Depends(get_db)):
    return _item_to_dict(svc.get_by_id(db, ChangeRequest, ws, item_id), db)


@router.put("/workspaces/{ws}/changes/requests/{item_id}")
def update_request(ws: str, item_id: int, body: dict,
                   current_user: Account = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    return _item_to_dict(svc.update_item(db, ws, "request", item_id, body), db)


@router.delete("/workspaces/{ws}/changes/requests/{item_id}", status_code=204)
def delete_request(ws: str, item_id: int,
                   current_user: Account = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    svc.delete_item(db, ChangeRequest, ws, item_id)


@router.put("/workspaces/{ws}/changes/requests/{item_id}/tags")
def set_request_tags(ws: str, item_id: int, body: dict,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    svc.set_tags(db, ChangeRequest, ws, item_id, body.get("tags", []))
    return _item_to_dict(svc.get_by_id(db, ChangeRequest, ws, item_id), db)


@router.post("/workspaces/{ws}/changes/requests/{item_id}/tags")
def add_request_tag(ws: str, item_id: int, body: dict,
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    svc.add_tag(db, ChangeRequest, ws, item_id, body.get("tag", ""))
    return _item_to_dict(svc.get_by_id(db, ChangeRequest, ws, item_id), db)


@router.delete("/workspaces/{ws}/changes/requests/{item_id}/tags/{tag_label}")
def remove_request_tag(ws: str, item_id: int, tag_label: str,
                       current_user: Account = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    svc.remove_tag(db, ChangeRequest, ws, item_id, tag_label)
    return _item_to_dict(svc.get_by_id(db, ChangeRequest, ws, item_id), db)


# ── Orders ──

@router.get("/workspaces/{ws}/changes/orders")
def list_orders(ws: str, current_user: Account = Depends(get_current_user),
                db: Session = Depends(get_db)):
    return [_item_to_dict(o, db) for o in svc.list_items(db, ws, "orders")]


@router.post("/workspaces/{ws}/changes/orders", status_code=201)
@router.post("/workspaces/{ws}/changes/orders/", status_code=201, include_in_schema=False)
def create_order(ws: str, body: dict,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    it = svc.create_item(db, ws, "order", body, current_user.login)
    return _item_to_dict(it, db)


@router.get("/workspaces/{ws}/changes/orders/{item_id}")
def get_order(ws: str, item_id: int,
              current_user: Account = Depends(get_current_user),
              db: Session = Depends(get_db)):
    return _item_to_dict(svc.get_by_id(db, ChangeOrder, ws, item_id), db)


@router.put("/workspaces/{ws}/changes/orders/{item_id}")
def update_order(ws: str, item_id: int, body: dict,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    return _item_to_dict(svc.update_item(db, ws, "order", item_id, body), db)


@router.delete("/workspaces/{ws}/changes/orders/{item_id}", status_code=204)
def delete_order(ws: str, item_id: int,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    svc.delete_item(db, ChangeOrder, ws, item_id)


@router.put("/workspaces/{ws}/changes/orders/{item_id}/tags")
def set_order_tags(ws: str, item_id: int, body: dict,
                   current_user: Account = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    svc.set_tags(db, ChangeOrder, ws, item_id, body.get("tags", []))
    return _item_to_dict(svc.get_by_id(db, ChangeOrder, ws, item_id), db)


@router.post("/workspaces/{ws}/changes/orders/{item_id}/tags")
def add_order_tag(ws: str, item_id: int, body: dict,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    svc.add_tag(db, ChangeOrder, ws, item_id, body.get("tag", ""))
    return _item_to_dict(svc.get_by_id(db, ChangeOrder, ws, item_id), db)


@router.delete("/workspaces/{ws}/changes/orders/{item_id}/tags/{tag_label}")
def remove_order_tag(ws: str, item_id: int, tag_label: str,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    svc.remove_tag(db, ChangeOrder, ws, item_id, tag_label)
    return _item_to_dict(svc.get_by_id(db, ChangeOrder, ws, item_id), db)


# ── Milestones ──

@router.get("/workspaces/{ws}/changes/milestones")
def list_milestones(ws: str, current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    return [_milestone_to_dict(m, db) for m in svc.list_items(db, ws, "milestones")]


@router.post("/workspaces/{ws}/changes/milestones", status_code=201)
@router.post("/workspaces/{ws}/changes/milestones/", status_code=201, include_in_schema=False)
def create_milestone(ws: str, body: dict,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    ms = svc.create_item(db, ws, "milestone", body, current_user.login)
    return _milestone_to_dict(ms, db)


@router.get("/workspaces/{ws}/changes/milestones/{item_id}")
def get_milestone(ws: str, item_id: int,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    return _milestone_to_dict(svc.get_by_id(db, Milestone, ws, item_id), db)


@router.put("/workspaces/{ws}/changes/milestones/{item_id}")
def update_milestone(ws: str, item_id: int, body: dict,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    return _milestone_to_dict(svc.update_item(db, ws, "milestone", item_id, body), db)


@router.delete("/workspaces/{ws}/changes/milestones/{item_id}", status_code=204)
def delete_milestone(ws: str, item_id: int,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    svc.delete_item(db, Milestone, ws, item_id)
