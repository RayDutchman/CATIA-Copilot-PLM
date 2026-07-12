"""里程碑（Milestone）端点路由。"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Response
from app.schemas.change import MilestoneDTO, ChangeRequestDTO, ChangeOrderDTO
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.models.change import ChangeIssue, ChangeRequest, ChangeOrder, Milestone
from app.services.change_manager import ChangeService
from app.services.factory.acl_factory import apply_acl, check_write_access
from app.routers.change_common import (
    _item_to_dict, _get_acl_dict, _check_workspace_access,
)

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
svc = ChangeService()


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
        writable = check_write_access(db, getattr(ms, "acl_id", None), current_user.login, is_admin,
                                      workspace_id=getattr(ms, "workspace_id", None))

    dd = getattr(ms, "due_date", None)
    data = dict(
        acl=_get_acl_dict(db, getattr(ms, "acl_id", None)) or {},
        description=getattr(ms, "description", "") or "",
        dueDate=dd.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dd.microsecond // 1000:03d}Z" if dd else None,
        id=ms.id,
        numberOfOrders=numberOfOrders,
        numberOfRequests=numberOfRequests,
        title=getattr(ms, "title", "") or "",
        workspaceId=getattr(ms, "workspace_id", ""),
        writable=writable,
    )
    return data


# ── Milestones ──

@router.get("/workspaces/{ws}/changes/milestones", response_model=List[MilestoneDTO])
@router.get("/workspaces/{ws}/changes/milestones/", include_in_schema=False)
def list_milestones(ws: str, current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    return [_milestone_to_dict(m, db, current_user) for m in svc.list_items(db, ws, "milestones")]


@router.post("/workspaces/{ws}/changes/milestones", status_code=201, response_model=MilestoneDTO)
@router.post("/workspaces/{ws}/changes/milestones/", status_code=201, include_in_schema=False)
def create_milestone(ws: str, body: dict,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    ms = svc.create_item(db, ws, "milestone", body, current_user.login)
    return _milestone_to_dict(ms, db, current_user)
@router.get("/workspaces/{ws}/changes/milestones/{item_id}", response_model=MilestoneDTO)
@router.get("/workspaces/{ws}/changes/milestones/{item_id}/", include_in_schema=False)
def get_milestone(ws: str, item_id: int,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    _check_workspace_access(db, ws, current_user.login)
    return _milestone_to_dict(svc.get_by_id(db, Milestone, ws, item_id), db, current_user)

@router.put("/workspaces/{ws}/changes/milestones/{item_id}", response_model=MilestoneDTO)
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
    is_admin = db.execute(sql_text(
        "SELECT 1 FROM usergroupmapping WHERE login=:l AND groupname='admin'"
    ), {"l": current_user.login}).first() is not None
    svc.delete_item(db, Milestone, ws, item_id, current_user.login, is_admin)


@router.get("/workspaces/{ws}/changes/milestones/{milestone_id}/requests", response_model=List[ChangeRequestDTO])
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


@router.get("/workspaces/{ws}/changes/milestones/{milestone_id}/orders", response_model=List[ChangeOrderDTO])
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
    return Response(status_code=204)
