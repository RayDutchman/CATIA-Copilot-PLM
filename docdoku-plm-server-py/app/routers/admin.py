"""管理员端点。"""
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.schemas.admin import (
    AdminAccountDTO, DiskUsageDTO, WorkspaceDTO,
    PlatformOptionsDTO, IndexStatusDTO,
)

router = APIRouter(prefix="/docdoku-plm-server-rest/api")


def _require_admin(db: Session, current_user: Account):
    """验证当前用户是全局管理员（usergroupmapping groupname='admin'），否则 403。"""
    is_admin = db.execute(text(
        "SELECT 1 FROM usergroupmapping WHERE login=:l AND groupname='admin'"
    ), {"l": current_user.login}).first()
    if not is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")


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
        "admin": r[4] or "",
        "creationDate": None,
    }


# ============ Account CRUD ============

@router.get("/admin/accounts", response_model=List[AdminAccountDTO])
@router.get("/admin/accounts/", include_in_schema=False)
def list_accounts(db: Session = Depends(get_db),
                  current_user: Account = Depends(get_current_user)):
    _require_admin(db, current_user)
    rows = db.execute(text(
        "SELECT a.login, a.email, a.name, a.language, a.enabled, u.workspace_id, "
        "CASE WHEN m.groupname IS NOT NULL THEN true ELSE false END AS is_admin "
        "FROM account a "
        "LEFT JOIN userdata u ON a.login = u.login "
        "LEFT JOIN usergroupmapping m ON a.login = m.login AND m.groupname = 'admin' "
        "ORDER BY a.login"
    )).fetchall()
    return [_account_to_dict(r) for r in rows]


@router.get("/admin/accounts/{login}", response_model=AdminAccountDTO)
@router.get("/admin/accounts/{login}/", include_in_schema=False)
def get_account(login: str, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    _require_admin(db, current_user)
    r = db.execute(text(
        "SELECT a.login, a.email, a.name, a.language, a.enabled, u.workspace_id, "
        "CASE WHEN m.groupname IS NOT NULL THEN true ELSE false END AS is_admin "
        "FROM account a "
        "LEFT JOIN userdata u ON a.login = u.login "
        "LEFT JOIN usergroupmapping m ON a.login = m.login AND m.groupname = 'admin' "
        "WHERE a.login = :login"
    ), {"login": login}).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="账户不存在")
    return _account_to_dict(r)


@router.put("/admin/accounts/{login}", response_model=AdminAccountDTO)
@router.put("/admin/accounts/{login}/", include_in_schema=False)
def update_account(login: str, body: dict, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    _require_admin(db, current_user)
    existing = db.execute(text(
        "SELECT login FROM account WHERE login = :login"
    ), {"login": login}).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="账户不存在")

    updates = {}
    if "email" in body:
        updates["email"] = body["email"]
    if "language" in body:
        updates["language"] = body["language"]
    if "enabled" in body:
        updates["enabled"] = body["enabled"]
    if "name" in body:
        updates["name"] = body["name"]

    if updates:
        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        db.execute(text(
            f"UPDATE account SET {set_clause} WHERE login = :login"
        ), {**updates, "login": login})
        db.commit()

    r = db.execute(text(
        "SELECT a.login, a.email, a.name, a.language, a.enabled, u.workspace_id, "
        "CASE WHEN m.groupname IS NOT NULL THEN true ELSE false END AS is_admin "
        "FROM account a "
        "LEFT JOIN userdata u ON a.login = u.login "
        "LEFT JOIN usergroupmapping m ON a.login = m.login AND m.groupname = 'admin' "
        "WHERE a.login = :login"
    ), {"login": login}).fetchone()
    return _account_to_dict(r)


@router.delete("/admin/accounts/{login}", status_code=204)
@router.delete("/admin/accounts/{login}/", status_code=204, include_in_schema=False)
def delete_account(login: str, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    _require_admin(db, current_user)
    existing = db.execute(text(
        "SELECT login FROM account WHERE login = :login"
    ), {"login": login}).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="账户不存在")

    db.execute(text("DELETE FROM credential WHERE login = :login"), {"login": login})
    db.execute(text("DELETE FROM userdata WHERE login = :login"), {"login": login})
    db.execute(text("DELETE FROM usergroupmapping WHERE login = :login"), {"login": login})
    db.execute(text("DELETE FROM account WHERE login = :login"), {"login": login})
    db.commit()


# ============ Workspace CRUD ============

@router.get("/admin/workspaces", response_model=List[WorkspaceDTO])
@router.get("/admin/workspaces/", include_in_schema=False)
def list_workspaces(db: Session = Depends(get_db),
                    current_user: Account = Depends(get_current_user)):
    _require_admin(db, current_user)
    rows = db.execute(text(
        "SELECT id, description, enabled, folderlocked, admin_login "
        "FROM workspace ORDER BY id"
    )).fetchall()
    return [_workspace_to_dict(r) for r in rows]


@router.get("/admin/workspaces/{ws}", response_model=WorkspaceDTO)
@router.get("/admin/workspaces/{ws}/", include_in_schema=False)
def get_workspace(ws: str, db: Session = Depends(get_db),
                  current_user: Account = Depends(get_current_user)):
    _require_admin(db, current_user)
    r = db.execute(text(
        "SELECT id, description, enabled, folderlocked, admin_login "
        "FROM workspace WHERE id = :id"
    ), {"id": ws}).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="工作区不存在")
    return _workspace_to_dict(r)


@router.put("/admin/workspaces/{ws}", response_model=WorkspaceDTO)
@router.put("/admin/workspaces/{ws}/", include_in_schema=False)
def update_workspace(ws: str, body: dict, db: Session = Depends(get_db),
                     current_user: Account = Depends(get_current_user)):
    _require_admin(db, current_user)
    existing = db.execute(text(
        "SELECT id FROM workspace WHERE id = :id"
    ), {"id": ws}).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="工作区不存在")

    updates = {}
    if "description" in body:
        updates["description"] = body["description"]
    if "enabled" in body:
        updates["enabled"] = body["enabled"]
    if "folderLocked" in body:
        updates["folderlocked"] = body["folderLocked"]

    if updates:
        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        db.execute(text(
            f"UPDATE workspace SET {set_clause} WHERE id = :id"
        ), {**updates, "id": ws})
        db.commit()

    r = db.execute(text(
        "SELECT id, description, enabled, folderlocked, admin_login "
        "FROM workspace WHERE id = :id"
    ), {"id": ws}).fetchone()
    return _workspace_to_dict(r)


@router.delete("/admin/workspaces/{ws}", status_code=204)
@router.delete("/admin/workspaces/{ws}/", status_code=204, include_in_schema=False)
def delete_workspace(ws: str, db: Session = Depends(get_db),
                     current_user: Account = Depends(get_current_user)):
    _require_admin(db, current_user)
    existing = db.execute(text(
        "SELECT id FROM workspace WHERE id = :id"
    ), {"id": ws}).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="工作区不存在")
    db.execute(text("DELETE FROM workspace WHERE id = :id"), {"id": ws})
    db.commit()


# ============ Platform Options ============

_STRATEGY_MAP = {0: "NONE", 1: "ADMIN_VALIDATION", None: "NONE"}
_STRATEGY_REVERSE = {"NONE": 0, "ADMIN_VALIDATION": 1}


def _to_strategy(val) -> str:
    return _STRATEGY_MAP.get(val, "NONE")


def _from_strategy(val: str) -> int:
    return _STRATEGY_REVERSE.get(val, 0)


@router.get("/admin/platform-options", response_model=PlatformOptionsDTO)
@router.get("/admin/platform-options/", include_in_schema=False)
def get_platform_options(db: Session = Depends(get_db)):
    row = db.execute(text(
        "SELECT workspacecreationstrategy, registrationstrategy "
        "FROM platformoptions LIMIT 1"
    )).first()
    if row:
        return {
            "workspaceCreationStrategy": _to_strategy(row[0]),
            "registrationStrategy": _to_strategy(row[1]),
        }
    return {"workspaceCreationStrategy": "NONE", "registrationStrategy": "NONE"}


@router.put("/admin/platform-options", response_model=PlatformOptionsDTO)
@router.put("/admin/platform-options/", include_in_schema=False)
def put_platform_options(body: dict, db: Session = Depends(get_db),
                        current_user: Account = Depends(get_current_user)):
    _require_admin(db, current_user)
    existing = db.execute(text(
        "SELECT id FROM platformoptions LIMIT 1"
    )).first()
    ws = _from_strategy(body.get("workspaceCreationStrategy", "NONE"))
    rs = _from_strategy(body.get("registrationStrategy", "NONE"))
    if existing:
        db.execute(text(
            "UPDATE platformoptions SET "
            "workspacecreationstrategy = :wcs, "
            "registrationstrategy = :rs"
        ), {"wcs": ws, "rs": rs})
    else:
        db.execute(text(
            "INSERT INTO platformoptions "
            "(id, workspacecreationstrategy, registrationstrategy) "
            "VALUES (1, :wcs, :rs)"
        ), {"wcs": ws, "rs": rs})
    db.commit()
    return get_platform_options(db)


# ============ Stats ============

def _get_admin_workspaces(db: Session, login: str) -> list[str]:
    """返回当前用户管理的 workspace 列表（全局 admin 看全部）。"""
    is_global = db.execute(text(
        "SELECT COUNT(*) FROM usergroupmapping WHERE login=:l AND groupname='admin'"
    ), {"l": login}).scalar() > 0
    if is_global:
        rows = db.execute(text("SELECT id FROM workspace ORDER BY id")).fetchall()
        return [r[0] for r in rows]
    rows = db.execute(text(
        "SELECT id FROM workspace WHERE admin_login=:l ORDER BY id"
    ), {"l": login}).fetchall()
    return [r[0] for r in rows]


@router.get("/admin/disk-usage-stats", response_model=Dict[str, DiskUsageDTO])
@router.get("/admin/disk-usage-stats/", include_in_schema=False)
def admin_disk_usage_stats(db: Session = Depends(get_db),
                           current_user: Account = Depends(get_current_user)):
    admin_ws = _get_admin_workspaces(db, current_user.login)
    result = {}
    for ws in admin_ws:
        docs_size = db.execute(text(
            "SELECT COALESCE(SUM(br.contentlength), 0) FROM binaryresource br "
            "JOIN documentiteration_binres dib ON br.fullname = dib.attachedfile_fullname "
            "WHERE dib.workspace_id = :ws"
        ), {"ws": ws}).scalar() or 0
        parts_size = db.execute(text(
            "SELECT COALESCE(SUM(br.contentlength), 0) FROM binaryresource br "
            "JOIN partiteration_binres pib ON br.fullname = pib.attachedfile_fullname "
            "WHERE pib.workspace_id = :ws"
        ), {"ws": ws}).scalar() or 0
        result[ws] = {"documents": docs_size, "parts": parts_size,
                       "partTemplates": 0, "documentTemplates": 0}
    return result


@router.get("/admin/users-stats", response_model=Dict[str, int])
@router.get("/admin/users-stats/", include_in_schema=False)
def admin_users_stats(db: Session = Depends(get_db),
                      current_user: Account = Depends(get_current_user)):
    admin_ws = _get_admin_workspaces(db, current_user.login)
    result = {}
    for ws in admin_ws:
        count = db.execute(text(
            "SELECT COUNT(*) FROM userdata WHERE workspace_id=:ws"
        ), {"ws": ws}).scalar() or 0
        result[ws] = count
    return result


@router.get("/admin/documents-stats", response_model=Dict[str, int])
@router.get("/admin/documents-stats/", include_in_schema=False)
def admin_documents_stats(db: Session = Depends(get_db),
                          current_user: Account = Depends(get_current_user)):
    admin_ws = _get_admin_workspaces(db, current_user.login)
    result = {}
    for ws in admin_ws:
        count = db.execute(text(
            "SELECT COUNT(*) FROM documentrevision WHERE workspace_id=:ws"
        ), {"ws": ws}).scalar() or 0
        result[ws] = count
    return result


@router.get("/admin/products-stats", response_model=Dict[str, int])
@router.get("/admin/products-stats/", include_in_schema=False)
def admin_products_stats(db: Session = Depends(get_db),
                         current_user: Account = Depends(get_current_user)):
    admin_ws = _get_admin_workspaces(db, current_user.login)
    result = {}
    for ws in admin_ws:
        count = db.execute(text(
            "SELECT COUNT(*) FROM configurationitem WHERE workspace_id=:ws"
        ), {"ws": ws}).scalar() or 0
        result[ws] = count
    return result


@router.get("/admin/parts-stats", response_model=Dict[str, int])
@router.get("/admin/parts-stats/", include_in_schema=False)
def admin_parts_stats(db: Session = Depends(get_db),
                      current_user: Account = Depends(get_current_user)):
    admin_ws = _get_admin_workspaces(db, current_user.login)
    result = {}
    for ws in admin_ws:
        count = db.execute(text(
            "SELECT COUNT(*) FROM partrevision WHERE workspace_id=:ws"
        ), {"ws": ws}).scalar() or 0
        result[ws] = count
    return result


# ============ Index ============

@router.post("/admin/index/{ws}", status_code=202)
@router.post("/admin/index/{ws}/", status_code=202, include_in_schema=False)
def post_index(ws: str, db: Session = Depends(get_db),
               current_user: Account = Depends(get_current_user)):
    try:
        import elasticsearch
        return {"status": "accepted"}
    except ImportError:
        return {"status": "accepted", "note": "ES not configured"}


# 保持旧 GET /admin/index 兼容
@router.get("/admin/index", response_model=IndexStatusDTO)
@router.get("/admin/index/", include_in_schema=False)
def get_index():
    return {"inProgress": False}


@router.put("/admin/workspace/{ws}/enable")
@router.put("/admin/workspace/{ws}/enable/", include_in_schema=False)
def enable_workspace(ws: str, enabled: bool = Query(True),
                     db: Session = Depends(get_db),
                     current_user: Account = Depends(get_current_user)):
    _require_admin(db, current_user)
    db.execute(text("UPDATE workspace SET enabled = :e WHERE id = :w"),
               {"e": enabled, "w": ws})
    db.commit()
    return {"status": "ok"}


@router.put("/admin/accounts/{login}/enable")
@router.put("/admin/accounts/{login}/enable/", include_in_schema=False)
def enable_account(login: str, enabled: bool = Query(True),
                   db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    _require_admin(db, current_user)
    db.execute(text("UPDATE account SET enabled = :e WHERE login = :l"),
               {"e": enabled, "l": login})
    db.commit()
    return {"status": "ok"}
