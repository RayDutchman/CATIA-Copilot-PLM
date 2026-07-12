from typing import List
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_global_admin
from app.core.exceptions import NotAllowedException
from app.models.auth import Account
from app.services.user_manager import user_mgmt_service
from app.schemas.user_mgmt import (
    UserDTOExtended, WorkspaceInfoDTO, AccountStatsDTO, WorkspaceStatsDTO,
)

router = APIRouter(prefix="/docdoku-plm-server-rest/api")


def _account_to_dict(acc, db):
    is_admin = user_mgmt_service.is_account_admin(db, acc.login)
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


@router.put("/accounts/me", response_model=UserDTOExtended)
@router.put("/accounts/me/", include_in_schema=False)
def update_account(body: dict, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    acc = user_mgmt_service.update_account(db, current_user.login, body)
    return _account_to_dict(acc, db)


@router.post("/accounts/create", status_code=201, response_model=UserDTOExtended)
@router.post("/accounts/create/", status_code=201, include_in_schema=False)
def create_account(body: dict, db: Session = Depends(get_db)):
    acc = user_mgmt_service.create_account(
        db, body.get("login", ""), body.get("password", ""),
        body.get("email", ""), body.get("name", ""), body.get("language", "en"))
    return _account_to_dict(acc, db)


@router.get("/accounts/workspaces", response_model=List[WorkspaceInfoDTO])
@router.get("/accounts/workspaces/", include_in_schema=False)
def list_workspaces(db: Session = Depends(get_db),
                    current_user: Account = Depends(get_current_user)):
    return user_mgmt_service.list_workspaces_for_user(db, current_user.login)


@router.get("/admin/accounts-stats", response_model=AccountStatsDTO)
@router.get("/admin/accounts-stats/", include_in_schema=False)
def accounts_stats(db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user),
                   _admin: Account = Depends(require_global_admin)):
    return user_mgmt_service.get_accounts_stats(db)


@router.get("/admin/workspace-stats", response_model=WorkspaceStatsDTO)
@router.get("/admin/workspace-stats/", include_in_schema=False)
def workspace_stats(db: Session = Depends(get_db),
                    current_user: Account = Depends(get_current_user),
                    _admin: Account = Depends(require_global_admin)):
    return user_mgmt_service.get_admin_workspace_stats(db)


@router.put("/accounts/gcm", status_code=204)
@router.put("/accounts/gcm/", status_code=204, include_in_schema=False)
def put_gcm(body: dict, db: Session = Depends(get_db),
            current_user: Account = Depends(get_current_user)):
    gcm_id = body.get("gcmId", "")
    if not gcm_id:
        raise NotAllowedException("NotAllowedException9", gcm_id)
    user_mgmt_service.put_gcm(db, current_user.login, gcm_id)
    return Response(status_code=204)


@router.delete("/accounts/gcm", status_code=204)
@router.delete("/accounts/gcm/", status_code=204, include_in_schema=False)
def delete_gcm(db: Session = Depends(get_db),
               current_user: Account = Depends(get_current_user)):
    user_mgmt_service.delete_gcm(db, current_user.login)
    return Response(status_code=204)

