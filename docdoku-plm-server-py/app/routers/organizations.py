"""组织管理端点。"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
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

router = APIRouter(prefix="/docdoku-plm-server-rest/api")


def _org_to_dict(r) -> dict:
    return {"name": r[0], "description": r[1] or ""}


@router.get("/organizations", response_model=OrganizationDTO)
@router.get("/organizations/", include_in_schema=False)
def list_organizations(
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    r = db.execute(text(
        "SELECT o.name, o.description FROM organization o "
        "JOIN organization_account oa ON o.name = oa.organization_name "
        "WHERE oa.account_login = :login"
    ), {"login": current_user.login}).fetchone()
    if not r:
        return {}
    return _org_to_dict(r)


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
    existing = db.execute(text(
        "SELECT name FROM organization WHERE name = :name"
    ), {"name": name}).fetchone()
    if existing:
        raise CreationException("OrganizationAlreadyExistsException", name)
    description = body.get("description", "")
    owner = current_user.login
    db.execute(text(
        "INSERT INTO organization (name, description, owner_login) "
        "VALUES (:name, :description, :owner)"
    ), {"name": name, "description": description, "owner": owner})
    db.commit()
    return {"name": name, "description": description, "owner": owner}


@router.get("/organizations/{org_name}", response_model=OrganizationDTO)
@router.get("/organizations/{org_name}/", include_in_schema=False)
def get_organization(
    org_name: str,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    r = db.execute(text(
        "SELECT name, description FROM organization WHERE name = :name"
    ), {"name": org_name}).fetchone()
    if not r:
        raise EntityNotFoundException("OrganizationNotFoundException", org_name)
    return _org_to_dict(r)


@router.put("/organizations/{org_name}", response_model=OrganizationDTO)
@router.put("/organizations/{org_name}/", include_in_schema=False)
def update_organization(
    org_name: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    existing = db.execute(text(
        "SELECT name, owner_login FROM organization WHERE name = :name"
    ), {"name": org_name}).fetchone()
    if not existing:
        raise EntityNotFoundException("OrganizationNotFoundException", org_name)
    if current_user.login != existing[1]:
        raise AccessRightException("AccessRightException")
    description = body.get("description", "")
    db.execute(text(
        "UPDATE organization SET description = :description WHERE name = :name"
    ), {"description": description, "name": org_name})
    db.commit()
    r = db.execute(text(
        "SELECT name, description FROM organization WHERE name = :name"
    ), {"name": org_name}).fetchone()
    return _org_to_dict(r)


@router.delete("/organizations/{org_name}", status_code=204)
@router.delete("/organizations/{org_name}/", status_code=204, include_in_schema=False)
def delete_organization(
    org_name: str,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    existing = db.execute(text(
        "SELECT name, owner_login FROM organization WHERE name = :name"
    ), {"name": org_name}).fetchone()
    if not existing:
        raise EntityNotFoundException("OrganizationNotFoundException", org_name)
    if current_user.login != existing[1]:
        raise AccessRightException("AccessRightException")
    db.execute(text(
        "DELETE FROM organization_account WHERE organization_name = :name"
    ), {"name": org_name})
    db.execute(text(
        "DELETE FROM organization WHERE name = :name"
    ), {"name": org_name})
    db.commit()


@router.put("/organizations/{org_name}/add-member")
@router.put("/organizations/{org_name}/add-member/", include_in_schema=False)
def add_member(
    org_name: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    existing = db.execute(text(
        "SELECT name FROM organization WHERE name = :name"
    ), {"name": org_name}).fetchone()
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
    existing_member = db.execute(text(
        "SELECT account_login FROM organization_account "
        "WHERE organization_name = :org AND account_login = :login"
    ), {"org": org_name, "login": login}).fetchone()
    if existing_member:
        return {"status": "already_member"}
    max_order = db.execute(text(
        "SELECT COALESCE(MAX(account_order), 0) FROM organization_account "
        "WHERE organization_name = :org"
    ), {"org": org_name}).scalar()
    db.execute(text(
        "INSERT INTO organization_account "
        "(organization_name, account_login, account_order) "
        "VALUES (:org, :login, :ord)"
    ), {"org": org_name, "login": login, "ord": max_order + 1})
    db.commit()
    return {"status": "ok"}


@router.put("/organizations/{org_name}/remove-member")
@router.put("/organizations/{org_name}/remove-member/", include_in_schema=False)
def remove_member(
    org_name: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    existing = db.execute(text(
        "SELECT name FROM organization WHERE name = :name"
    ), {"name": org_name}).fetchone()
    if not existing:
        raise EntityNotFoundException("OrganizationNotFoundException", org_name)
    login = body.get("login", "").strip()
    if not login:
        raise NotAllowedException("NotAllowedException9", login)
    db.execute(text(
        "DELETE FROM organization_account "
        "WHERE organization_name = :org AND account_login = :login"
    ), {"org": org_name, "login": login})
    db.commit()
    return {"status": "ok"}


@router.put("/organizations/{org_name}/move-member")
@router.put("/organizations/{org_name}/move-member/", include_in_schema=False)
def move_member(
    org_name: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    existing = db.execute(text(
        "SELECT name, owner_login FROM organization WHERE name = :name"
    ), {"name": org_name}).fetchone()
    if not existing:
        raise EntityNotFoundException("OrganizationNotFoundException", org_name)
    if current_user.login != existing[1]:
        raise AccessRightException("AccessRightException")
    login = body.get("login", "").strip()
    if not login:
        raise NotAllowedException("NotAllowedException9", login)
    members = db.execute(text(
        "SELECT account_login, account_order FROM organization_account "
        "WHERE organization_name = :org ORDER BY account_order"
    ), {"org": org_name}).fetchall()
    idx = None
    for i, (l, _) in enumerate(members):
        if l == login:
            idx = i
            break
    if idx is None:
        raise EntityNotFoundException("OrganizationNotFoundException", org_name)
    if idx == 0:
        return {"status": "ok"}
    prev_login, prev_order = members[idx - 1]
    cur_order = members[idx][1]
    db.execute(text(
        "UPDATE organization_account SET account_order = :ord "
        "WHERE organization_name = :org AND account_login = :login"
    ), {"ord": prev_order, "org": org_name, "login": login})
    db.execute(text(
        "UPDATE organization_account SET account_order = :ord "
        "WHERE organization_name = :org AND account_login = :login"
    ), {"ord": cur_order, "org": org_name, "login": prev_login})
    db.commit()
    return {"status": "ok"}
