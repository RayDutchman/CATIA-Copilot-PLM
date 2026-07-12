"""组织管理端点。"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import (
    AccessRightException, CreationException, EntityAlreadyExistsException,
    EntityNotFoundException, NotAllowedException,
)
from app.models.auth import Account
from app.schemas.misc import OrganizationDTO, OrganizationMemberResultDTO
from app.services.organization_manager import organization_service

router = APIRouter(prefix="/docdoku-plm-server-rest/api")


def _org_to_dict(r) -> dict:
    if isinstance(r, dict):
        return {"name": r["name"], "description": r.get("description") or "",
                "owner": r.get("owner_login")}
    return {"name": r[0], "description": r[1] or "",
            "owner": r[2] if len(r) > 2 else None}


@router.get("/organizations", response_model=OrganizationDTO | None)
@router.get("/organizations/", include_in_schema=False)
def list_organizations(
    response: Response,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    """返回当前用户的组织（Java 为 'my organization' 模型）。无组织时返回 204。"""
    org = organization_service.list_user_organizations(db, current_user.login)
    if not org:
        response.status_code = 204
        return None
    return _org_to_dict(org)


@router.post("/organizations", status_code=201, response_model=OrganizationDTO)
@router.post("/organizations/", status_code=201, include_in_schema=False)
def create_organization(
    body: dict,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    name = body.get("name", "").strip()
    if not name:
        raise CreationException("NotAllowedException9", name)
    description = body.get("description", "")
    owner = current_user.login
    return organization_service.create_organization(db, name, description, owner)


@router.get("/organizations/{org_name}", response_model=OrganizationDTO)
@router.get("/organizations/{org_name}/", include_in_schema=False)
def get_organization(
    org_name: str,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    org = organization_service.get_org_by_name(db, org_name)
    if not org:
        raise EntityNotFoundException("OrganizationNotFoundException", org_name)
    return _org_to_dict(org)


@router.put("/organizations/{org_name}", response_model=OrganizationDTO)
@router.put("/organizations/{org_name}/", include_in_schema=False)
def update_organization(
    org_name: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    existing = organization_service.get_org_by_name(db, org_name)
    if not existing:
        raise EntityNotFoundException("OrganizationNotFoundException", org_name)
    if current_user.login != existing["owner_login"]:
        raise AccessRightException("AccessRightException", current_user.login)
    description = body.get("description", "")
    organization_service.update_organization_desc(db, org_name, description)
    org = organization_service.get_org_by_name(db, org_name)
    return _org_to_dict(org)


@router.delete("/organizations/{org_name}", status_code=204)
@router.delete("/organizations/{org_name}/", status_code=204, include_in_schema=False)
def delete_organization(
    org_name: str,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    existing = organization_service.get_org_by_name(db, org_name)
    if not existing:
        raise EntityNotFoundException("OrganizationNotFoundException", org_name)
    if current_user.login != existing["owner_login"]:
        raise AccessRightException("AccessRightException", current_user.login)
    organization_service.delete_org(db, org_name)


@router.put("/organizations/{org_name}/add-member")
@router.put("/organizations/{org_name}/add-member/", include_in_schema=False)
def add_member(
    org_name: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    existing = organization_service.get_org_by_name(db, org_name)
    if not existing:
        raise EntityNotFoundException("OrganizationNotFoundException", org_name)
    login = body.get("login", "").strip()
    if not login:
        raise NotAllowedException("NotAllowedException9", login)
    user = db.execute(text(
        "SELECT login FROM account WHERE login = :login"
    ), {"login": login}).fetchone()
    if not user:
        raise EntityNotFoundException("AccountNotFoundException", login)
    if organization_service.add_member(db, org_name, login):
        return {"status": "ok"}
    return {"status": "already_member"}


@router.put("/organizations/{org_name}/remove-member")
@router.put("/organizations/{org_name}/remove-member/", include_in_schema=False)
def remove_member(
    org_name: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    existing = organization_service.get_org_by_name(db, org_name)
    if not existing:
        raise EntityNotFoundException("OrganizationNotFoundException", org_name)
    login = body.get("login", "").strip()
    if not login:
        raise NotAllowedException("NotAllowedException9", login)
    organization_service.remove_member(db, org_name, login)
    return {"status": "ok"}


@router.put("/organizations/{org_name}/move-member")
@router.put("/organizations/{org_name}/move-member/", include_in_schema=False)
def move_member(
    org_name: str,
    body: dict,
    direction: str = Query(...),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    existing = organization_service.get_org_by_name(db, org_name)
    if not existing:
        raise EntityNotFoundException("OrganizationNotFoundException", org_name)
    if current_user.login != existing["owner_login"]:
        raise AccessRightException("AccessRightException", current_user.login)
    login = body.get("login", "").strip()
    if not login:
        raise NotAllowedException("NotAllowedException9", login)
    if direction not in ("up", "down"):
        raise HTTPException(status_code=400, detail="Invalid direction, must be 'up' or 'down'")
    members = organization_service.get_members_ordered(db, org_name)
    idx = None
    for i, (l, _) in enumerate(members):
        if l == login:
            idx = i
            break
    if idx is None:
        raise EntityNotFoundException("OrganizationNotFoundException", org_name)
    if direction == "up":
        if idx == 0:
            return Response(status_code=204)
        swap_login, swap_order = members[idx - 1]
    else:  # down
        if idx == len(members) - 1:
            return Response(status_code=204)
        swap_login, swap_order = members[idx + 1]
    cur_order = members[idx][1]
    organization_service.swap_member_order(db, org_name, login, cur_order, swap_login, swap_order)
    return Response(status_code=204)
