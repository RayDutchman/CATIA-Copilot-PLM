"""工作区 CRUD 端点。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account

router = APIRouter(prefix="/docdoku-plm-server-rest/api")


def _row_to_dict(r) -> dict:
    return {
        "id": r[0],
        "description": r[1] or "",
        "enabled": bool(r[2]) if r[2] is not None else True,
        "folderLocked": bool(r[3]) if r[3] is not None else False,
        "admin": r[4] or "",
        "creationDate": None,
    }


@router.get("/workspaces")
def list_workspaces(db: Session = Depends(get_db),
                    current_user: Account = Depends(get_current_user)):
    rows = db.execute(text(
        "SELECT id, description, admin_login FROM workspace ORDER BY id"
    )).fetchall()
    all_ws = [{"id": r[0], "description": r[1] or "", "admin": r[2] or ""} for r in rows]
    admin_ws = [w for w in all_ws if w["admin"] == current_user.login]
    return {"administratedWorkspaces": admin_ws, "allWorkspaces": all_ws}


@router.get("/workspaces/reachable-users")
def reachable_users(db: Session = Depends(get_db),
                    current_user: Account = Depends(get_current_user)):
    """Payara 的 getReachableUsersForCaller。返回除当前用户外的所有账号。"""
    from app.models.auth import Account as Acct
    users = db.query(Acct).filter(Acct.login != current_user.login).all()
    return [{"login": u.login, "name": u.name, "email": u.email} for u in users]


@router.get("/workspaces/{ws}/stats-overview")
def stats_overview(ws: str, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    products = db.execute(text("SELECT COUNT(*) FROM configurationitem WHERE workspace_id=:w"), {"w": ws}).scalar() or 0
    parts = db.execute(text("SELECT COUNT(*) FROM partmaster WHERE workspace_id=:w"), {"w": ws}).scalar() or 0
    docs = db.execute(text("SELECT COUNT(*) FROM documentmaster WHERE workspace_id=:w"), {"w": ws}).scalar() or 0
    users = db.execute(text("SELECT COUNT(*) FROM userdata WHERE workspace_id=:w"), {"w": ws}).scalar() or 0
    return {"parts": parts, "documents": docs, "users": users, "products": products}


@router.get("/workspaces/{ws}/disk-usage")
def disk_usage(ws: str, db: Session = Depends(get_db),
               current_user: Account = Depends(get_current_user)):
    return {"total": 0}


@router.get("/workspaces/{ws}")
def get_workspace(ws: str, db: Session = Depends(get_db),
                  current_user: Account = Depends(get_current_user)):
    r = db.execute(text(
        "SELECT id, description, enabled, folderlocked, admin_login "
        "FROM workspace WHERE id = :id"
    ), {"id": ws}).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="工作区不存在")
    return _row_to_dict(r)


@router.post("/workspaces", status_code=201)
@router.post("/workspaces/", status_code=201, include_in_schema=False)
def create_workspace(body: dict, db: Session = Depends(get_db),
                     current_user: Account = Depends(get_current_user),
                     userLogin: str = Query(None)):
    ws_id = body.get("id", "").strip()
    if not ws_id:
        raise HTTPException(status_code=400, detail="工作区 id 不能为空")

    existing = db.execute(text(
        "SELECT id FROM workspace WHERE id = :id"
    ), {"id": ws_id}).fetchone()
    if existing:
        raise HTTPException(status_code=409, detail="工作区已存在")

    admin = userLogin or current_user.login
    desc = body.get("description", "")
    folder_locked = body.get("folderLocked", False)

    db.execute(text(
        "INSERT INTO workspace (id, description, enabled, folderlocked, admin_login) "
        "VALUES (:id, :desc, TRUE, :folder_locked, :admin)"
    ), {"id": ws_id, "desc": desc, "folder_locked": folder_locked, "admin": admin})
    db.commit()

    return {
        "id": ws_id,
        "description": desc,
        "enabled": True,
        "folderLocked": folder_locked,
        "admin": admin,
        "creationDate": None,
    }


@router.put("/workspaces/{ws}")
@router.put("/workspaces/{ws}/", include_in_schema=False)
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
    return _row_to_dict(r)


@router.delete("/workspaces/{ws}", status_code=204)
def delete_workspace(ws: str, db: Session = Depends(get_db),
                     current_user: Account = Depends(get_current_user)):
    existing = db.execute(text(
        "SELECT id FROM workspace WHERE id = :id"
    ), {"id": ws}).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="工作区不存在")
    db.execute(text("DELETE FROM workspace WHERE id = :id"), {"id": ws})
    db.commit()
