"""角色管理 REST 端点。"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import AccessRightException
from app.models.auth import Account
from app.services.security_service import security_service
from app.schemas.misc import RoleDTO

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
PREFIX = "/workspaces/{ws}"


def _role_to_dict(r, db: Session) -> dict:
    return security_service.role_to_dict(r, db)


@router.get(f"{PREFIX}/roles", response_model=List[RoleDTO])
@router.get(f"{PREFIX}/roles/", include_in_schema=False)
def list_roles(ws: str, db: Session = Depends(get_db),
               current_user: Account = Depends(get_current_user)):
    return [_role_to_dict(r, db) for r in security_service.list_roles(db, ws)]


@router.get(f"{PREFIX}/roles/inuse", response_model=List[RoleDTO])
@router.get(f"{PREFIX}/roles/inuse/", include_in_schema=False)
def list_roles_in_use(ws: str, db: Session = Depends(get_db),
                      current_user: Account = Depends(get_current_user)):
    return [_role_to_dict(r, db) for r in security_service.list_roles_in_use(db, ws)]


@router.post(f"{PREFIX}/roles", status_code=201, response_model=RoleDTO)
@router.post(f"{PREFIX}/roles/", status_code=201, include_in_schema=False)
def create_role(ws: str, body: dict, db: Session = Depends(get_db),
                                current_user: Account = Depends(get_current_user)):

    r = security_service.create_role(db, ws, body.get("name", ""),
                                     current_user.login,
                                     body.get("defaultAssignedUsers"),
                                     body.get("defaultAssignedGroups"))
    return _role_to_dict(r, db)


@router.put(f"{PREFIX}/roles/{{name}}", response_model=RoleDTO)
@router.put(f"{PREFIX}/roles/{{name}}/", include_in_schema=False)
def update_role(ws: str, name: str, body: dict, db: Session = Depends(get_db),
                                current_user: Account = Depends(get_current_user)):

    r = security_service.update_role(db, ws, name,
                                     current_user.login,
                                     body.get("defaultAssignedUsers"),
                                     body.get("defaultAssignedGroups"))
    return _role_to_dict(r, db)


@router.delete(f"{PREFIX}/roles/{{name}}", status_code=204)
@router.delete(f"{PREFIX}/roles/{{name}}/", status_code=204, include_in_schema=False)
def delete_role(ws: str, name: str, db: Session = Depends(get_db),
                                current_user: Account = Depends(get_current_user)):

    security_service.delete_role(db, ws, name, current_user.login)

