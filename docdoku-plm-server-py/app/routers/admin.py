"""管理员端点。"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account

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
        "admin": r[4] or "",
        "creationDate": None,
    }


# ============ Account CRUD ============

@router.get("/admin/accounts")
@router.get("/admin/accounts/", include_in_schema=False)
def list_accounts(db: Session = Depends(get_db),
                  current_user: Account = Depends(get_current_user)):
    rows = db.execute(text(
        "SELECT a.login, a.email, a.name, a.language, a.enabled, u.workspace_id, "
        "CASE WHEN m.groupname IS NOT NULL THEN true ELSE false END AS is_admin "
        "FROM account a "
        "LEFT JOIN userdata u ON a.login = u.login "
        "LEFT JOIN usergroupmapping m ON a.login = m.login AND m.groupname = 'admin' "
        "ORDER BY a.login"
    )).fetchall()
    return [_account_to_dict(r) for r in rows]


@router.get("/admin/accounts/{login}")
@router.get("/admin/accounts/{login}/", include_in_schema=False)
def get_account(login: str, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
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


@router.put("/admin/accounts/{login}")
@router.put("/admin/accounts/{login}/", include_in_schema=False)
def update_account(login: str, body: dict, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
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

@router.get("/admin/workspaces")
@router.get("/admin/workspaces/", include_in_schema=False)
def list_workspaces(db: Session = Depends(get_db),
                    current_user: Account = Depends(get_current_user)):
    rows = db.execute(text(
        "SELECT id, description, enabled, folderlocked, admin_login "
        "FROM workspace ORDER BY id"
    )).fetchall()
    return [_workspace_to_dict(r) for r in rows]


@router.get("/admin/workspaces/{ws}")
@router.get("/admin/workspaces/{ws}/", include_in_schema=False)
def get_workspace(ws: str, db: Session = Depends(get_db),
                  current_user: Account = Depends(get_current_user)):
    r = db.execute(text(
        "SELECT id, description, enabled, folderlocked, admin_login "
        "FROM workspace WHERE id = :id"
    ), {"id": ws}).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="工作区不存在")
    return _workspace_to_dict(r)


@router.put("/admin/workspaces/{ws}")
@router.put("/admin/workspaces/{ws}/", include_in_schema=False)
def update_workspace(ws: str, body: dict, db: Session = Depends(get_db),
                     current_user: Account = Depends(get_current_user)):
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


@router.get("/admin/platform-options")
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


@router.put("/admin/platform-options")
@router.put("/admin/platform-options/", include_in_schema=False)
def put_platform_options(body: dict, db: Session = Depends(get_db)):
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


# ============ Index ============

@router.get("/admin/index")
@router.get("/admin/index/", include_in_schema=False)
def get_index():
    return {"inProgress": False}


@router.post("/admin/index", status_code=202)
@router.post("/admin/index/", status_code=202, include_in_schema=False)
def post_index():
    return {"status": "accepted"}

