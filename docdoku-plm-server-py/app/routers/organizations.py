"""组织管理端点（stub 实现）。"""
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account

router = APIRouter(prefix="/docdoku-plm-server-rest/api")


@router.get("/organizations")
def list_organizations(
    current_user: Account = Depends(get_current_user),
):
    return []


@router.post("/organizations")
@router.post("/organizations/", include_in_schema=False)
def create_organization(
    body: dict,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    return {"status": "ok"}


@router.get("/organizations/{org_id}")
def get_organization(
    org_id: str,
    current_user: Account = Depends(get_current_user),
):
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="组织不存在")


@router.put("/organizations/{org_id}")
@router.put("/organizations/{org_id}/", include_in_schema=False)
def update_organization(
    org_id: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    return {"status": "ok"}


@router.delete("/organizations/{org_id}", status_code=204)
def delete_organization(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    pass


@router.put("/organizations/{org_id}/add-member")
@router.put("/organizations/{org_id}/add-member/", include_in_schema=False)
def add_member(
    org_id: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    return {"status": "ok"}


@router.put("/organizations/{org_id}/remove-member")
@router.put("/organizations/{org_id}/remove-member/", include_in_schema=False)
def remove_member(
    org_id: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    return {"status": "ok"}


@router.put("/organizations/{org_id}/move-member")
@router.put("/organizations/{org_id}/move-member/", include_in_schema=False)
def move_member(
    org_id: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    return {"status": "ok"}
