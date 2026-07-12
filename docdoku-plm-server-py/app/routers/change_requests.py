"""变更请求（ChangeRequest）端点路由。"""
from typing import List
from fastapi import APIRouter, Depends
from app.schemas.change import ChangeRequestDTO
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.models.change import ChangeRequest
from app.services.change_manager import ChangeService
from app.services.factory.acl_factory import apply_acl
from app.routers.change_common import (
    _item_to_dict, _check_workspace_access,
    _set_affected_parts, _set_affected_documents,
)

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
svc = ChangeService()


# ── Requests ──

@router.get("/workspaces/{ws}/changes/requests", response_model=List[ChangeRequestDTO])
@router.get("/workspaces/{ws}/changes/requests/", include_in_schema=False)
def list_requests(ws: str, current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    is_admin = svc.is_admin(db, current_user.login)
    return [_item_to_dict(r, db, current_user)
            for r in svc.list_items(db, ws, "requests",
                                     user_login=current_user.login,
                                     is_admin=is_admin)]


@router.post("/workspaces/{ws}/changes/requests", status_code=201, response_model=ChangeRequestDTO)
@router.post("/workspaces/{ws}/changes/requests/", status_code=201, include_in_schema=False)
def create_request(ws: str, body: dict,
                   current_user: Account = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    it = svc.create_item(db, ws, "request", body, current_user.login)
    return _item_to_dict(it, db, current_user)


@router.get("/workspaces/{ws}/changes/requests/link", response_model=List[ChangeRequestDTO])
@router.get("/workspaces/{ws}/changes/requests/link/", include_in_schema=False)
def search_requests(ws: str, q: str = "",
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    items = db.query(ChangeRequest).filter(
        ChangeRequest.workspace_id == ws,
        ChangeRequest.name.ilike(f'%{q}%')
    ).limit(8).all()
    return [_item_to_dict(r, db, current_user) for r in items]


@router.get("/workspaces/{ws}/changes/requests/{item_id}", response_model=ChangeRequestDTO)
@router.get("/workspaces/{ws}/changes/requests/{item_id}/", include_in_schema=False)
def get_request(ws: str, item_id: int,
                current_user: Account = Depends(get_current_user),
                db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    return _item_to_dict(svc.get_by_id(db, ChangeRequest, ws, item_id), db, current_user)


@router.put("/workspaces/{ws}/changes/requests/{item_id}", response_model=ChangeRequestDTO)
@router.put("/workspaces/{ws}/changes/requests/{item_id}/", include_in_schema=False)
def update_request(ws: str, item_id: int, body: dict,
                   current_user: Account = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    is_admin = svc.is_admin(db, current_user.login)
    return _item_to_dict(svc.update_item(db, ws, "request", item_id, body,
                                          user_login=current_user.login,
                                          is_admin=is_admin), db, current_user)


@router.delete("/workspaces/{ws}/changes/requests/{item_id}", status_code=204)
@router.delete("/workspaces/{ws}/changes/requests/{item_id}/", status_code=204, include_in_schema=False)
def delete_request(ws: str, item_id: int,
                   current_user: Account = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    is_admin = svc.is_admin(db, current_user.login)
    svc.delete_item(db, ChangeRequest, ws, item_id, current_user.login, is_admin)


@router.put("/workspaces/{ws}/changes/requests/{item_id}/tags", response_model=ChangeRequestDTO)
@router.put("/workspaces/{ws}/changes/requests/{item_id}/tags/", include_in_schema=False)
def set_request_tags(ws: str, item_id: int, body: dict,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    is_admin = svc.is_admin(db, current_user.login)
    tags_raw = body.get("tags", [])
    if tags_raw and isinstance(tags_raw, list) and isinstance(tags_raw[0], dict):
        tags = [t.get("label", "") for t in tags_raw]
    else:
        tags = [str(t) for t in tags_raw] if tags_raw else []
    svc.set_tags(db, ChangeRequest, ws, item_id, tags,
                 user_login=current_user.login, is_admin=is_admin)
    return _item_to_dict(svc.get_by_id(db, ChangeRequest, ws, item_id), db, current_user)


@router.post("/workspaces/{ws}/changes/requests/{item_id}/tags", response_model=ChangeRequestDTO)
@router.post("/workspaces/{ws}/changes/requests/{item_id}/tags/", include_in_schema=False)
def add_request_tag(ws: str, item_id: int, body: dict,
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    if "tags" in body and isinstance(body["tags"], list):
        for t in body["tags"]:
            label = t.get("label", "") if isinstance(t, dict) else str(t)
            svc.add_tag(db, ChangeRequest, ws, item_id, label)
    else:
        svc.add_tag(db, ChangeRequest, ws, item_id, body.get("tag", ""))
    return _item_to_dict(svc.get_by_id(db, ChangeRequest, ws, item_id), db, current_user)


@router.delete("/workspaces/{ws}/changes/requests/{item_id}/tags/{tag_label}", response_model=ChangeRequestDTO)
@router.delete("/workspaces/{ws}/changes/requests/{item_id}/tags/{tag_label}/", include_in_schema=False)
def remove_request_tag(ws: str, item_id: int, tag_label: str,
                       current_user: Account = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    svc.remove_tag(db, ChangeRequest, ws, item_id, tag_label)
    return _item_to_dict(svc.get_by_id(db, ChangeRequest, ws, item_id), db, current_user)


@router.put("/workspaces/{ws}/changes/requests/{item_id}/affected-documents")
@router.put("/workspaces/{ws}/changes/requests/{item_id}/affected-documents/", include_in_schema=False)
def set_request_affected_documents(ws: str, item_id: int, body: dict,

                                   current_user: Account = Depends(get_current_user),
                                   db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    is_admin = svc.is_admin(db, current_user.login)
    _set_affected_documents(db, ws, item_id, body.get("documents", []),
                            "changereq_affected_document", "changerequest_id",
                            user_login=current_user.login, is_admin=is_admin)
    it = svc.get_by_id(db, ChangeRequest, ws, item_id)
    return _item_to_dict(it, db, current_user)


@router.put("/workspaces/{ws}/changes/requests/{item_id}/affected-parts")
@router.put("/workspaces/{ws}/changes/requests/{item_id}/affected-parts/", include_in_schema=False)
def set_request_affected_parts(ws: str, item_id: int, body: dict,

                                current_user: Account = Depends(get_current_user),
                                db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    is_admin = svc.is_admin(db, current_user.login)
    _set_affected_parts(db, ws, item_id, body.get("parts", []),
                        "changereq_affected_part", "changerequest_id",
                        user_login=current_user.login, is_admin=is_admin)
    it = svc.get_by_id(db, ChangeRequest, ws, item_id)
    return _item_to_dict(it, db, current_user)


@router.put("/workspaces/{ws}/changes/requests/{item_id}/affected-issues")
@router.put("/workspaces/{ws}/changes/requests/{item_id}/affected-issues/", include_in_schema=False)
def set_request_affected_issues(ws: str, item_id: int, body: dict,

                                 current_user: Account = Depends(get_current_user),
                                 db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    svc.set_request_affected_issues(db, ws, item_id, body.get("issues", []))
    it = svc.get_by_id(db, ChangeRequest, ws, item_id)
    return _item_to_dict(it, db, current_user)


@router.put("/workspaces/{ws}/changes/requests/{item_id}/acl")
@router.put("/workspaces/{ws}/changes/requests/{item_id}/acl/", include_in_schema=False)
def set_request_acl(ws: str, item_id: int, body: dict,
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    item = svc.get_by_id(db, ChangeRequest, ws, item_id)
    new_acl_id = apply_acl(db, item.acl_id,
                           body.get("userEntries", {}),
                           body.get("groupEntries", {}),
                           workspace_id=ws)
    item.acl_id = new_acl_id
    db.commit()
    return _item_to_dict(item, db, current_user)
