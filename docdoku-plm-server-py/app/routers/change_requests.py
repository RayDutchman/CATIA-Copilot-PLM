"""变更请求（ChangeRequest）端点路由。"""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import AccessRightException
from app.models.auth import Account
from app.models.change import ChangeIssue, ChangeRequest, ChangeOrder
from app.services.change_manager import ChangeService
from app.services.acl_helper import apply_acl

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
svc = ChangeService()

_NAME_CACHE: dict = {}


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


def _item_to_dict(item, db: Optional[Session] = None) -> dict:
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

    data = dict(
        acl=None,
        affectedDocuments=[],
        affectedParts=[],
        assignee=None,
        assigneeName=assignee_name or None,
        author=author_login,
        authorName=author_name or author_login,
        category=getattr(item, "category", None),
        creationDate=creation_date,
        description=getattr(item, "description", "") or "",
        id=item.id,
        name=name,
        priority=getattr(item, "priority", None),
        tags=[t.label for t in (getattr(item, "tags", None) or [])],
        workspaceId=getattr(item, "workspace_id", ""),
        writable=True,
    )

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
                data["addressedChangeIssues"] = [_item_to_dict(i, db) for i in issues]
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
                data["addressedChangeRequests"] = [_item_to_dict(r, db) for r in requests]
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


# ── Requests ──

@router.get("/workspaces/{ws}/changes/requests")
@router.get("/workspaces/{ws}/changes/requests/", include_in_schema=False)
def list_requests(ws: str, current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    return [_item_to_dict(r, db) for r in svc.list_items(db, ws, "requests")]


@router.post("/workspaces/{ws}/changes/requests", status_code=201)
@router.post("/workspaces/{ws}/changes/requests/", status_code=201, include_in_schema=False)
def create_request(ws: str, body: dict,
                   current_user: Account = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    it = svc.create_item(db, ws, "request", body, current_user.login)
    return _item_to_dict(it, db)


@router.get("/workspaces/{ws}/changes/requests/link")
@router.get("/workspaces/{ws}/changes/requests/link/", include_in_schema=False)
def search_requests(ws: str, q: str = "",
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    items = db.query(ChangeRequest).filter(
        ChangeRequest.workspace_id == ws,
        ChangeRequest.name.ilike(f'%{q}%')
    ).limit(8).all()
    return [_item_to_dict(r, db) for r in items]


@router.get("/workspaces/{ws}/changes/requests/{item_id}")
@router.get("/workspaces/{ws}/changes/requests/{item_id}/", include_in_schema=False)
def get_request(ws: str, item_id: int,
                current_user: Account = Depends(get_current_user),
                db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    return _item_to_dict(svc.get_by_id(db, ChangeRequest, ws, item_id), db)


@router.put("/workspaces/{ws}/changes/requests/{item_id}")
@router.put("/workspaces/{ws}/changes/requests/{item_id}/", include_in_schema=False)
def update_request(ws: str, item_id: int, body: dict,
                   current_user: Account = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    return _item_to_dict(svc.update_item(db, ws, "request", item_id, body), db)


@router.delete("/workspaces/{ws}/changes/requests/{item_id}", status_code=204)
@router.delete("/workspaces/{ws}/changes/requests/{item_id}/", status_code=204, include_in_schema=False)
def delete_request(ws: str, item_id: int,
                   current_user: Account = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    svc.delete_item(db, ChangeRequest, ws, item_id)


@router.put("/workspaces/{ws}/changes/requests/{item_id}/tags")
@router.put("/workspaces/{ws}/changes/requests/{item_id}/tags/", include_in_schema=False)
def set_request_tags(ws: str, item_id: int, body: dict,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    svc.set_tags(db, ChangeRequest, ws, item_id, body.get("tags", []))
    return _item_to_dict(svc.get_by_id(db, ChangeRequest, ws, item_id), db)


@router.post("/workspaces/{ws}/changes/requests/{item_id}/tags")
@router.post("/workspaces/{ws}/changes/requests/{item_id}/tags/", include_in_schema=False)
def add_request_tag(ws: str, item_id: int, body: dict,
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    svc.add_tag(db, ChangeRequest, ws, item_id, body.get("tag", ""))
    return _item_to_dict(svc.get_by_id(db, ChangeRequest, ws, item_id), db)


@router.delete("/workspaces/{ws}/changes/requests/{item_id}/tags/{tag_label}")
@router.delete("/workspaces/{ws}/changes/requests/{item_id}/tags/{tag_label}/", include_in_schema=False)
def remove_request_tag(ws: str, item_id: int, tag_label: str,
                       current_user: Account = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    svc.remove_tag(db, ChangeRequest, ws, item_id, tag_label)
    return _item_to_dict(svc.get_by_id(db, ChangeRequest, ws, item_id), db)


@router.put("/workspaces/{ws}/changes/requests/{item_id}/affected-documents")
@router.put("/workspaces/{ws}/changes/requests/{item_id}/affected-documents/", include_in_schema=False)
def set_request_affected_documents(ws: str, item_id: int, body: dict,

                                   current_user: Account = Depends(get_current_user),
                                   db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    _set_affected_documents(db, ws, item_id, body.get("documents", []),
                            "changereq_affected_document", "changerequest_id")
    return {"status": "ok"}


@router.put("/workspaces/{ws}/changes/requests/{item_id}/affected-parts")
@router.put("/workspaces/{ws}/changes/requests/{item_id}/affected-parts/", include_in_schema=False)
def set_request_affected_parts(ws: str, item_id: int, body: dict,

                                current_user: Account = Depends(get_current_user),
                                db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    _set_affected_parts(db, ws, item_id, body.get("parts", []),
                        "changereq_affected_part", "changerequest_id")
    return {"status": "ok"}


@router.put("/workspaces/{ws}/changes/requests/{item_id}/affected-issues")
@router.put("/workspaces/{ws}/changes/requests/{item_id}/affected-issues/", include_in_schema=False)
def set_request_affected_issues(ws: str, item_id: int, body: dict,

                                 current_user: Account = Depends(get_current_user),
                                 db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    db.execute(sql_text(
        "DELETE FROM changerequest_changeissue WHERE changerequest_id=:iid"
    ), {"iid": item_id})
    issues = body.get("issues", [])
    for issue_data in issues:
        issue_id = issue_data.get("id") if isinstance(issue_data, dict) else issue_data
        if issue_id:
            db.execute(sql_text(
                "INSERT INTO changerequest_changeissue (changerequest_id, changeissue_id) "
                "VALUES (:rid, :iid)"
            ), {"rid": item_id, "iid": issue_id})
    db.commit()
    return {"status": "ok"}


@router.put("/workspaces/{ws}/changes/requests/{item_id}/acl")
@router.put("/workspaces/{ws}/changes/requests/{item_id}/acl/", include_in_schema=False)
def set_request_acl(ws: str, item_id: int, body: dict,
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    item = svc.get_by_id(db, ChangeRequest, ws, item_id)
    new_acl_id = apply_acl(db, item.acl_id,
                           body.get("userEntries", {}),
                           body.get("groupEntries", {}))
    item.acl_id = new_acl_id
    db.commit()
    return {"aclId": new_acl_id}
