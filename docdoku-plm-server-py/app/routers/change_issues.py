"""变更问题（ChangeIssue）端点路由。"""
from typing import Optional, List
from fastapi import APIRouter, Depends
from app.schemas.change import ChangeIssueDTO
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import AccessRightException
from app.models.auth import Account
from app.models.change import ChangeIssue, ChangeRequest, ChangeOrder
from app.models.security import AclUserEntry, AclUserGroupEntry
from app.services.change_manager import ChangeService
from app.services.acl_helper import apply_acl, check_write_access

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
        "userEntries": [{"key": r.principal_login, "value": _PERMISSION_NAMES.get(r.permission, "FORBIDDEN")} for r in user_rows],
        "groupEntries": [{"key": r.principal_id, "value": _PERMISSION_NAMES.get(r.permission, "FORBIDDEN")} for r in group_rows],
        "userEntriesMap": {r.principal_login: _PERMISSION_NAMES.get(r.permission, "FORBIDDEN") for r in user_rows},
        "userGroupEntriesMap": {},
    }


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


# ── Issues ──

@router.get("/workspaces/{ws}/changes/issues", response_model=List[ChangeIssueDTO])
@router.get("/workspaces/{ws}/changes/issues/", include_in_schema=False)
def list_issues(ws: str, current_user: Account = Depends(get_current_user),
                db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    return [_item_to_dict(i, db, current_user) for i in svc.list_items(db, ws, "issues")]


@router.post("/workspaces/{ws}/changes/issues", status_code=201, response_model=ChangeIssueDTO)
@router.post("/workspaces/{ws}/changes/issues/", status_code=201, include_in_schema=False)
def create_issue(ws: str, body: dict,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    it = svc.create_item(db, ws, "issue", body, current_user.login)
    return _item_to_dict(it, db, current_user)


@router.get("/workspaces/{ws}/changes/issues/link", response_model=List[ChangeIssueDTO])
@router.get("/workspaces/{ws}/changes/issues/link/", include_in_schema=False)
def search_issues(ws: str, q: str = "",
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    items = db.query(ChangeIssue).filter(
        ChangeIssue.workspace_id == ws,
        ChangeIssue.name.ilike(f'%{q}%')
    ).limit(8).all()
    return [_item_to_dict(i, db, current_user) for i in items]


@router.get("/workspaces/{ws}/changes/issues/{item_id}", response_model=ChangeIssueDTO)
@router.get("/workspaces/{ws}/changes/issues/{item_id}/", include_in_schema=False)
def get_issue(ws: str, item_id: int,
              current_user: Account = Depends(get_current_user),
              db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    return _item_to_dict(svc.get_by_id(db, ChangeIssue, ws, item_id), db, current_user)


@router.put("/workspaces/{ws}/changes/issues/{item_id}", response_model=ChangeIssueDTO)
@router.put("/workspaces/{ws}/changes/issues/{item_id}/", include_in_schema=False)
def update_issue(ws: str, item_id: int, body: dict,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    return _item_to_dict(svc.update_item(db, ws, "issue", item_id, body), db, current_user)


@router.delete("/workspaces/{ws}/changes/issues/{item_id}", status_code=204)
@router.delete("/workspaces/{ws}/changes/issues/{item_id}/", status_code=204, include_in_schema=False)
def delete_issue(ws: str, item_id: int,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    svc.delete_item(db, ChangeIssue, ws, item_id)


@router.put("/workspaces/{ws}/changes/issues/{item_id}/tags", response_model=ChangeIssueDTO)
@router.put("/workspaces/{ws}/changes/issues/{item_id}/tags/", include_in_schema=False)
def set_issue_tags(ws: str, item_id: int, body: dict,
                   current_user: Account = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    svc.set_tags(db, ChangeIssue, ws, item_id, body.get("tags", []))
    it = svc.get_by_id(db, ChangeIssue, ws, item_id)
    return _item_to_dict(it, db, current_user)


@router.post("/workspaces/{ws}/changes/issues/{item_id}/tags", response_model=ChangeIssueDTO)
@router.post("/workspaces/{ws}/changes/issues/{item_id}/tags/", include_in_schema=False)
def add_issue_tag(ws: str, item_id: int, body: dict,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    svc.add_tag(db, ChangeIssue, ws, item_id, body.get("tag", ""))
    it = svc.get_by_id(db, ChangeIssue, ws, item_id)
    return _item_to_dict(it, db, current_user)


@router.delete("/workspaces/{ws}/changes/issues/{item_id}/tags/{tag_label}", response_model=ChangeIssueDTO)
@router.delete("/workspaces/{ws}/changes/issues/{item_id}/tags/{tag_label}/", include_in_schema=False)
def remove_issue_tag(ws: str, item_id: int, tag_label: str,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    svc.remove_tag(db, ChangeIssue, ws, item_id, tag_label)
    it = svc.get_by_id(db, ChangeIssue, ws, item_id)
    return _item_to_dict(it, db, current_user)


@router.put("/workspaces/{ws}/changes/issues/{item_id}/affected-documents")
@router.put("/workspaces/{ws}/changes/issues/{item_id}/affected-documents/", include_in_schema=False)
def set_issue_affected_documents(ws: str, item_id: int, body: dict,

                                 current_user: Account = Depends(get_current_user),
                                 db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    _set_affected_documents(db, ws, item_id, body.get("documents", []),
                            "changeissue_affected_document", "changeissue_id")
    return {"status": "ok"}


@router.put("/workspaces/{ws}/changes/issues/{item_id}/affected-parts")
@router.put("/workspaces/{ws}/changes/issues/{item_id}/affected-parts/", include_in_schema=False)
def set_issue_affected_parts(ws: str, item_id: int, body: dict,

                              current_user: Account = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    _set_affected_parts(db, ws, item_id, body.get("parts", []),
                        "changeissue_affected_part", "changeissue_id")
    return {"status": "ok"}


@router.put("/workspaces/{ws}/changes/issues/{item_id}/acl")
@router.put("/workspaces/{ws}/changes/issues/{item_id}/acl/", include_in_schema=False)
def set_issue_acl(ws: str, item_id: int, body: dict,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    item = svc.get_by_id(db, ChangeIssue, ws, item_id)
    new_acl_id = apply_acl(db, item.acl_id,
                           body.get("userEntries", {}),
                           body.get("groupEntries", {}))
    item.acl_id = new_acl_id
    db.commit()
    return {"aclId": new_acl_id}
