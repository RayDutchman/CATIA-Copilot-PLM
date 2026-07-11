"""变更命令（ChangeOrder）端点路由。"""
from typing import List
from fastapi import APIRouter, Depends
from app.schemas.change import ChangeOrderDTO
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.models.change import ChangeOrder
from app.services.change_manager import ChangeService
from app.services.factory.acl_factory import apply_acl
from app.routers.change_common import (
    _item_to_dict, _check_workspace_access,
    _set_affected_parts, _set_affected_documents,
)

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
svc = ChangeService()


# ── Orders ──

@router.get("/workspaces/{ws}/changes/orders", response_model=List[ChangeOrderDTO])
@router.get("/workspaces/{ws}/changes/orders/", include_in_schema=False)
def list_orders(ws: str, current_user: Account = Depends(get_current_user),
                db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    is_admin = db.execute(sql_text(
        "SELECT 1 FROM usergroupmapping WHERE login=:l AND groupname='admin'"
    ), {"l": current_user.login}).first() is not None
    return [_item_to_dict(o, db, current_user)
            for o in svc.list_items(db, ws, "orders",
                                     user_login=current_user.login,
                                     is_admin=is_admin)]


@router.post("/workspaces/{ws}/changes/orders", status_code=201, response_model=ChangeOrderDTO)
@router.post("/workspaces/{ws}/changes/orders/", status_code=201, include_in_schema=False)
def create_order(ws: str, body: dict,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    it = svc.create_item(db, ws, "order", body, current_user.login)
    return _item_to_dict(it, db, current_user)


@router.get("/workspaces/{ws}/changes/orders/link", response_model=List[ChangeOrderDTO])
@router.get("/workspaces/{ws}/changes/orders/link/", include_in_schema=False)
def search_orders(ws: str, q: str = "",
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    items = db.query(ChangeOrder).filter(
        ChangeOrder.workspace_id == ws,
        ChangeOrder.name.ilike(f'%{q}%')
    ).limit(8).all()
    return [_item_to_dict(o, db, current_user) for o in items]


@router.get("/workspaces/{ws}/changes/orders/{item_id}", response_model=ChangeOrderDTO)
@router.get("/workspaces/{ws}/changes/orders/{item_id}/", include_in_schema=False)
def get_order(ws: str, item_id: int,
              current_user: Account = Depends(get_current_user),
              db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    return _item_to_dict(svc.get_by_id(db, ChangeOrder, ws, item_id), db, current_user)


@router.put("/workspaces/{ws}/changes/orders/{item_id}", response_model=ChangeOrderDTO)
@router.put("/workspaces/{ws}/changes/orders/{item_id}/", include_in_schema=False)
def update_order(ws: str, item_id: int, body: dict,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    is_admin = db.execute(sql_text(
        "SELECT 1 FROM usergroupmapping WHERE login=:l AND groupname='admin'"
    ), {"l": current_user.login}).first() is not None
    return _item_to_dict(svc.update_item(db, ws, "order", item_id, body,
                                          user_login=current_user.login,
                                          is_admin=is_admin), db, current_user)


@router.delete("/workspaces/{ws}/changes/orders/{item_id}", status_code=204)
@router.delete("/workspaces/{ws}/changes/orders/{item_id}/", status_code=204, include_in_schema=False)
def delete_order(ws: str, item_id: int,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    is_admin = db.execute(sql_text(
        "SELECT 1 FROM usergroupmapping WHERE login=:l AND groupname='admin'"
    ), {"l": current_user.login}).first() is not None
    svc.delete_item(db, ChangeOrder, ws, item_id, current_user.login, is_admin)


@router.put("/workspaces/{ws}/changes/orders/{item_id}/tags", response_model=ChangeOrderDTO)
@router.put("/workspaces/{ws}/changes/orders/{item_id}/tags/", include_in_schema=False)
def set_order_tags(ws: str, item_id: int, body: dict,
                   current_user: Account = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    tags_raw = body.get("tags", [])
    if tags_raw and isinstance(tags_raw, list) and isinstance(tags_raw[0], dict):
        tags = [t.get("label", "") for t in tags_raw]
    else:
        tags = [str(t) for t in tags_raw] if tags_raw else []
    svc.set_tags(db, ChangeOrder, ws, item_id, tags)
    return _item_to_dict(svc.get_by_id(db, ChangeOrder, ws, item_id), db, current_user)


@router.post("/workspaces/{ws}/changes/orders/{item_id}/tags", response_model=ChangeOrderDTO)
@router.post("/workspaces/{ws}/changes/orders/{item_id}/tags/", include_in_schema=False)
def add_order_tag(ws: str, item_id: int, body: dict,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    if "tags" in body and isinstance(body["tags"], list):
        for t in body["tags"]:
            label = t.get("label", "") if isinstance(t, dict) else str(t)
            svc.add_tag(db, ChangeOrder, ws, item_id, label)
    else:
        svc.add_tag(db, ChangeOrder, ws, item_id, body.get("tag", ""))
    return _item_to_dict(svc.get_by_id(db, ChangeOrder, ws, item_id), db, current_user)


@router.delete("/workspaces/{ws}/changes/orders/{item_id}/tags/{tag_label}", response_model=ChangeOrderDTO)
@router.delete("/workspaces/{ws}/changes/orders/{item_id}/tags/{tag_label}/", include_in_schema=False)
def remove_order_tag(ws: str, item_id: int, tag_label: str,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    svc.remove_tag(db, ChangeOrder, ws, item_id, tag_label)
    return _item_to_dict(svc.get_by_id(db, ChangeOrder, ws, item_id), db, current_user)


@router.put("/workspaces/{ws}/changes/orders/{item_id}/affected-documents")
@router.put("/workspaces/{ws}/changes/orders/{item_id}/affected-documents/", include_in_schema=False)
def set_order_affected_documents(ws: str, item_id: int, body: dict,

                                 current_user: Account = Depends(get_current_user),
                                 db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    is_admin = db.execute(sql_text(
        "SELECT 1 FROM usergroupmapping WHERE login=:l AND groupname='admin'"
    ), {"l": current_user.login}).first() is not None
    _set_affected_documents(db, ws, item_id, body.get("documents", []),
                            "changeorder_affected_document", "changeorder_id",
                            user_login=current_user.login, is_admin=is_admin)
    it = svc.get_by_id(db, ChangeOrder, ws, item_id)
    return _item_to_dict(it, db, current_user)


@router.put("/workspaces/{ws}/changes/orders/{item_id}/affected-parts")
@router.put("/workspaces/{ws}/changes/orders/{item_id}/affected-parts/", include_in_schema=False)
def set_order_affected_parts(ws: str, item_id: int, body: dict,

                              current_user: Account = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    is_admin = db.execute(sql_text(
        "SELECT 1 FROM usergroupmapping WHERE login=:l AND groupname='admin'"
    ), {"l": current_user.login}).first() is not None
    _set_affected_parts(db, ws, item_id, body.get("parts", []),
                        "changeorder_affected_part", "changeorder_id",
                        user_login=current_user.login, is_admin=is_admin)
    it = svc.get_by_id(db, ChangeOrder, ws, item_id)
    return _item_to_dict(it, db, current_user)


@router.put("/workspaces/{ws}/changes/orders/{item_id}/affected-requests")
@router.put("/workspaces/{ws}/changes/orders/{item_id}/affected-requests/", include_in_schema=False)
def set_order_affected_requests(ws: str, item_id: int, body: dict,

                                 current_user: Account = Depends(get_current_user),
                                 db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    db.execute(sql_text(
        "DELETE FROM changeorder_changerequest WHERE changeorder_id=:iid"
    ), {"iid": item_id})
    requests = body.get("requests", [])
    for req_data in requests:
        req_id = req_data.get("id") if isinstance(req_data, dict) else req_data
        if req_id:
            db.execute(sql_text(
                "INSERT INTO changeorder_changerequest (changeorder_id, changerequest_id) "
                "VALUES (:oid, :rid)"
            ), {"oid": item_id, "rid": req_id})
    db.commit()
    it = svc.get_by_id(db, ChangeOrder, ws, item_id)
    return _item_to_dict(it, db, current_user)


@router.put("/workspaces/{ws}/changes/orders/{item_id}/acl")
@router.put("/workspaces/{ws}/changes/orders/{item_id}/acl/", include_in_schema=False)
def set_order_acl(ws: str, item_id: int, body: dict,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    item = svc.get_by_id(db, ChangeOrder, ws, item_id)
    new_acl_id = apply_acl(db, item.acl_id,
                           body.get("userEntries", {}),
                           body.get("groupEntries", {}))
    item.acl_id = new_acl_id
    db.commit()
    return _item_to_dict(item, db, current_user)
