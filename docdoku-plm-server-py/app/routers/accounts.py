from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.user_mgmt_service import user_mgmt_service

router = APIRouter(prefix="/docdoku-plm-server-rest/api")


def _account_to_dict(acc, db):
    is_admin = db.execute(text(
        "SELECT 1 FROM usergroupmapping WHERE login = :l AND groupname = 'admin'"
    ), {"l": acc.login}).first() is not None
    result = {
        "login": acc.login,
        "email": acc.email or "",
        "name": acc.name or "",
        "language": acc.language or "en",
        "enabled": bool(acc.enabled) if acc.enabled is not None else True,
        "admin": is_admin,
        "timeZone": acc.timezone or "",
    }
    return result


@router.get("/accounts/me")
def get_account(db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    """返回当前登录用户信息（与 Payara getMyAccount 一致）。"""
    return _account_to_dict(current_user, db)


@router.put("/accounts/me")
@router.put("/accounts/me/", include_in_schema=False)
def update_account(body: dict, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    acc = user_mgmt_service.update_account(db, current_user.login, body)
    return _account_to_dict(acc, db)


@router.post("/accounts/create", status_code=201)
@router.post("/accounts/create/", status_code=201, include_in_schema=False)
def create_account(body: dict, db: Session = Depends(get_db)):
    acc = user_mgmt_service.create_account(
        db, body.get("login", ""), body.get("password", ""),
        body.get("email", ""), body.get("name", ""), body.get("language", "en"))
    return _account_to_dict(acc, db)


@router.get("/accounts/workspaces")
def list_workspaces(db: Session = Depends(get_db),
                    current_user: Account = Depends(get_current_user)):
    return user_mgmt_service.list_workspaces_for_user(db, current_user.login)


@router.get("/admin/accounts-stats")
def accounts_stats(db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    from sqlalchemy import text
    total = db.execute(text("SELECT COUNT(*) FROM account")).scalar()
    enabled = db.execute(text("SELECT COUNT(*) FROM account WHERE enabled = true")).scalar()
    disabled = total - enabled if total else 0
    return {"totalAccounts": total or 0, "enabledAccounts": enabled or 0,
            "disabledAccounts": disabled}


@router.get("/admin/workspace-stats")
def workspace_stats(db: Session = Depends(get_db),
                    current_user: Account = Depends(get_current_user)):
    from sqlalchemy import text
    total = db.execute(text("SELECT COUNT(*) FROM workspace")).scalar()
    enabled = db.execute(text("SELECT COUNT(*) FROM workspace WHERE enabled = true")).scalar()
    return {"totalWorkspaces": total or 0, "enabledWorkspaces": enabled or 0}
