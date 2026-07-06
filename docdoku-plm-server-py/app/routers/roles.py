"""角色管理 REST 端点。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.security_service import security_service

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
PREFIX = "/workspaces/{ws}"


def _role_to_dict(r, db: Session) -> dict:
    from sqlalchemy import text
    users = db.execute(text(
        "SELECT user_login FROM role_user WHERE role_name=:n AND role_workspace_id=:w"
    ), {"n": r.name, "w": r.workspace_id}).fetchall()
    groups = db.execute(text(
        "SELECT usergroup_id FROM role_usergroup WHERE role_name=:n AND role_workspace_id=:w"
    ), {"n": r.name, "w": r.workspace_id}).fetchall()
    user_logins = [u[0] for u in users]
    accounts = {a.login: a.name for a in db.query(Account).filter(
        Account.login.in_(user_logins)).all()} if user_logins else {}
    return {
        "id": f"{r.workspace_id}:{r.name}",
        "name": r.name,
        "workspaceId": r.workspace_id,
        "defaultAssignedUsers": [{"login": login, "name": accounts.get(login, login)}
                                  for login in user_logins],
        "defaultAssignedGroups": [{"id": g[0]} for g in groups],
    }


@router.get(f"{PREFIX}/roles")
@router.get(f"{PREFIX}/roles/", include_in_schema=False)
def list_roles(ws: str, db: Session = Depends(get_db),
               current_user: Account = Depends(get_current_user)):
    return [_role_to_dict(r, db) for r in security_service.list_roles(db, ws)]


@router.get(f"{PREFIX}/roles/inuse")
@router.get(f"{PREFIX}/roles/inuse/", include_in_schema=False)
def list_roles_in_use(ws: str, db: Session = Depends(get_db),
                      current_user: Account = Depends(get_current_user)):
    return [_role_to_dict(r, db) for r in security_service.list_roles_in_use(db, ws)]


@router.post(f"{PREFIX}/roles", status_code=201)
@router.post(f"{PREFIX}/roles/", status_code=201, include_in_schema=False)
def create_role(ws: str, body: dict, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    r = security_service.create_role(db, ws, body.get("name", ""),
                                     body.get("defaultAssignedUsers"),
                                     body.get("defaultAssignedGroups"))
    return _role_to_dict(r, db)


@router.put(f"{PREFIX}/roles/{{name}}")
@router.put(f"{PREFIX}/roles/{{name}}/", include_in_schema=False)
def update_role(ws: str, name: str, body: dict, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    r = security_service.update_role(db, ws, name,
                                     body.get("defaultAssignedUsers"),
                                     body.get("defaultAssignedGroups"))
    return _role_to_dict(r, db)


@router.delete(f"{PREFIX}/roles/{{name}}", status_code=204)
@router.delete(f"{PREFIX}/roles/{{name}}/", status_code=204, include_in_schema=False)
def delete_role(ws: str, name: str, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    security_service.delete_role(db, ws, name)

