"""变更问题（ChangeIssue）端点路由。"""
from typing import List
from fastapi import APIRouter, Depends
from app.schemas.change import ChangeIssueDTO
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.models.change import ChangeIssue
from app.services.change_manager import ChangeService
from app.services.acl_helper import apply_acl
from app.routers.change_common import (
    _item_to_dict, _check_workspace_access,
    _set_affected_parts, _set_affected_documents,
)

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
svc = ChangeService()


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
    tags_raw = body.get("tags", [])
    if tags_raw and isinstance(tags_raw, list) and isinstance(tags_raw[0], dict):
        tags = [t.get("label", "") for t in tags_raw]
    else:
        tags = [str(t) for t in tags_raw] if tags_raw else []
    svc.set_tags(db, ChangeIssue, ws, item_id, tags)
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
    return _item_to_dict(item, db, current_user)
