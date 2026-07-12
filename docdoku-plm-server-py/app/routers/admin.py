"""管理员端点。"""
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_global_admin
from app.core.exceptions import (
    AccessRightException, EntityNotFoundException, WorkspaceNotFoundException,
)
from app.models.auth import Account
from app.schemas.admin import (
    AdminAccountDTO, DiskUsageDTO, WorkspaceDTO,
    PlatformOptionsDTO, IndexStatusDTO,
)
from app.services.account_manager import account_service
from app.services.workspace_manager import workspace_service
from app.services.platform_options_manager import platform_options_service

router = APIRouter(prefix="/docdoku-plm-server-rest/api")


def _account_to_dict(r) -> dict:
    return {
        "login": r[0],
        "email": r[1] or "",
        "name": r[2] or "",
        "language": r[3] or "",
        "enabled": bool(r[4]) if r[4] is not None else True,
        "workspaceId": r[5] or None,
        "admin": bool(r[6]) if r[6] is not None else False,
    }


def _workspace_to_dict(r) -> dict:
    return {
        "id": r[0],
        "description": r[1] or "",
        "enabled": bool(r[2]) if r[2] is not None else True,
        "folderLocked": bool(r[3]) if r[3] is not None else False,
    }


# ============ Account CRUD ============

@router.get("/admin/accounts", response_model=List[AdminAccountDTO])
@router.get("/admin/accounts/", include_in_schema=False)
def list_accounts(db: Session = Depends(get_db),
                  _admin: Account = Depends(require_global_admin)):
    rows = account_service.list_accounts_admin(db)
    return [_account_to_dict(r) for r in rows]


@router.get("/admin/accounts/{login}", response_model=AdminAccountDTO)
@router.get("/admin/accounts/{login}/", include_in_schema=False)
def get_account(login: str, db: Session = Depends(get_db),
                _admin: Account = Depends(require_global_admin)):
    r = account_service.get_account_admin(db, login)
    if not r:
        raise EntityNotFoundException("AccountNotFoundException", login)
    return _account_to_dict(r)


@router.put("/admin/accounts/{login}", response_model=AdminAccountDTO)
@router.put("/admin/accounts/{login}/", include_in_schema=False)
def update_account(login: str, body: dict, db: Session = Depends(get_db),
                   _admin: Account = Depends(require_global_admin)):
    r = account_service.update_account_admin(db, login, body)
    return _account_to_dict(r)


@router.delete("/admin/accounts/{login}", status_code=204)
@router.delete("/admin/accounts/{login}/", status_code=204, include_in_schema=False)
def delete_account(login: str, db: Session = Depends(get_db),
                   _admin: Account = Depends(require_global_admin)):
    account_service.delete_account_cascade(db, login)


# ============ Workspace CRUD ============

@router.get("/admin/workspaces", response_model=List[WorkspaceDTO])
@router.get("/admin/workspaces/", include_in_schema=False)
def list_workspaces(db: Session = Depends(get_db),
                    _admin: Account = Depends(require_global_admin)):
    rows = workspace_service.list_workspaces_admin(db)
    return [_workspace_to_dict(r) for r in rows]


@router.get("/admin/workspaces/{ws}", response_model=WorkspaceDTO)
@router.get("/admin/workspaces/{ws}/", include_in_schema=False)
def get_workspace(ws: str, db: Session = Depends(get_db),
                  _admin: Account = Depends(require_global_admin)):
    r = workspace_service.get_workspace_admin(db, ws)
    return _workspace_to_dict(r)


@router.put("/admin/workspaces/{ws}", response_model=WorkspaceDTO)
@router.put("/admin/workspaces/{ws}/", include_in_schema=False)
def update_workspace(ws: str, body: dict, db: Session = Depends(get_db),
                     _admin: Account = Depends(require_global_admin)):
    r = workspace_service.update_workspace_admin(db, ws, body)
    return _workspace_to_dict(r)


@router.delete("/admin/workspaces/{ws}", status_code=204)
@router.delete("/admin/workspaces/{ws}/", status_code=204, include_in_schema=False)
def delete_workspace(ws: str, db: Session = Depends(get_db),
                     _admin: Account = Depends(require_global_admin)):
    workspace_service.get_workspace_admin(db, ws)  # 存在性校验
    workspace_service.delete_workspace(db, ws)


# ============ Platform Options ============

_STRATEGY_MAP = {0: "NONE", 1: "ADMIN_VALIDATION", None: "NONE"}
_STRATEGY_REVERSE = {"NONE": 0, "ADMIN_VALIDATION": 1}


def _to_strategy(val) -> str:
    return _STRATEGY_MAP.get(val, "NONE")


def _from_strategy(val: str) -> int:
    return _STRATEGY_REVERSE.get(val, 0)


@router.get("/admin/platform-options", response_model=PlatformOptionsDTO)
@router.get("/admin/platform-options/", include_in_schema=False)
def get_platform_options(db: Session = Depends(get_db),
                         _admin: Account = Depends(require_global_admin)):
    opts = platform_options_service.get_platform_options(db)
    return {
        "workspaceCreationStrategy": _to_strategy(opts.get("workspacecreationstrategy")),
        "registrationStrategy": _to_strategy(opts.get("registrationstrategy")),
    }


@router.put("/admin/platform-options", status_code=204)
@router.put("/admin/platform-options/", status_code=204, include_in_schema=False)
def put_platform_options(body: dict, db: Session = Depends(get_db),
                        _admin: Account = Depends(require_global_admin)):
    ws_val = _from_strategy(body.get("workspaceCreationStrategy", "NONE"))
    rs_val = _from_strategy(body.get("registrationStrategy", "NONE"))
    platform_options_service.upsert_platform_options(db, ws_val, rs_val)
    return Response(status_code=204)


# ============ Stats ============

@router.get("/admin/disk-usage-stats", response_model=Dict[str, int])
@router.get("/admin/disk-usage-stats/", include_in_schema=False)
def admin_disk_usage_stats(db: Session = Depends(get_db),
                           current_user: Account = Depends(get_current_user),
                           _admin: Account = Depends(require_global_admin)):
    return account_service.get_disk_usage_stats(db, current_user.login)


@router.get("/admin/users-stats", response_model=Dict[str, int])
@router.get("/admin/users-stats/", include_in_schema=False)
def admin_users_stats(db: Session = Depends(get_db),
                      current_user: Account = Depends(get_current_user),
                      _admin: Account = Depends(require_global_admin)):
    return account_service.get_users_stats(db, current_user.login)


@router.get("/admin/documents-stats", response_model=Dict[str, int])
@router.get("/admin/documents-stats/", include_in_schema=False)
def admin_documents_stats(db: Session = Depends(get_db),
                          current_user: Account = Depends(get_current_user),
                          _admin: Account = Depends(require_global_admin)):
    return account_service.get_documents_stats(db, current_user.login)


@router.get("/admin/products-stats", response_model=Dict[str, int])
@router.get("/admin/products-stats/", include_in_schema=False)
def admin_products_stats(db: Session = Depends(get_db),
                         current_user: Account = Depends(get_current_user),
                         _admin: Account = Depends(require_global_admin)):
    return account_service.get_products_stats(db, current_user.login)


@router.get("/admin/parts-stats", response_model=Dict[str, int])
@router.get("/admin/parts-stats/", include_in_schema=False)
def admin_parts_stats(db: Session = Depends(get_db),
                      current_user: Account = Depends(get_current_user),
                      _admin: Account = Depends(require_global_admin)):
    return account_service.get_parts_stats(db, current_user.login)


# ============ Index ============

@router.put("/admin/index/{ws}", status_code=202)
@router.put("/admin/index/{ws}/", status_code=202, include_in_schema=False)
def put_index(ws: str, db: Session = Depends(get_db),
              current_user: Account = Depends(get_current_user),
              _admin: Account = Depends(require_global_admin)):
    try:
        import elasticsearch
        return {"status": "accepted"}
    except ImportError:
        return {"status": "accepted", "note": "ES not configured"}


# 保持旧 GET /admin/index 兼容
@router.get("/admin/index", response_model=IndexStatusDTO)
@router.get("/admin/index/", include_in_schema=False)
def get_index(db: Session = Depends(get_db),
              _admin: Account = Depends(require_global_admin)):

    return {"inProgress": False}


@router.put("/admin/workspace/{ws}/enable", response_model=WorkspaceDTO)
@router.put("/admin/workspace/{ws}/enable/", include_in_schema=False)
def enable_workspace(ws: str, enabled: bool = Query(True),
                     db: Session = Depends(get_db),
                     _admin: Account = Depends(require_global_admin)):
    r = workspace_service.enable_workspace_admin(db, ws, enabled)
    return _workspace_to_dict(r)


@router.put("/admin/accounts/{login}/enable", response_model=AdminAccountDTO)
@router.put("/admin/accounts/{login}/enable/", include_in_schema=False)
def enable_account(login: str, enabled: bool = Query(True),
                   db: Session = Depends(get_db),
                   _admin: Account = Depends(require_global_admin)):
    r = account_service.enable_account_admin(db, login, enabled)
    return _account_to_dict(r)
