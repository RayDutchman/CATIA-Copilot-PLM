"""工作区 CRUD 端点。"""
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
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
@router.get("/workspaces/", include_in_schema=False)
def list_workspaces(db: Session = Depends(get_db),
                    current_user: Account = Depends(get_current_user)):
    rows = db.execute(text(
        "SELECT id, description, admin_login FROM workspace ORDER BY id"
    )).fetchall()
    all_ws = [{"id": r[0], "description": r[1] or "", "admin": r[2] or ""} for r in rows]

    # 全局管理员（usergroupmapping groupname='admin'）看全部 workspace
    is_global_admin = db.execute(text(
        "SELECT COUNT(*) FROM usergroupmapping WHERE login=:l AND groupname='admin'"
    ), {"l": current_user.login}).scalar() > 0
    if is_global_admin:
        return {"administratedWorkspaces": all_ws, "allWorkspaces": all_ws}

    admin_ws = [w for w in all_ws if w["admin"] == current_user.login]
    user_ws_ids = db.execute(text(
        "SELECT workspace_id FROM userdata WHERE login=:l"
    ), {"l": current_user.login}).fetchall()
    user_ws = {r[0] for r in user_ws_ids}
    return {"administratedWorkspaces": admin_ws,
            "allWorkspaces": [w for w in all_ws if w["id"] in user_ws]}


@router.get("/workspaces/more")
@router.get("/workspaces/more/", include_in_schema=False)
def list_more_workspaces(db: Session = Depends(get_db),
                         current_user: Account = Depends(get_current_user)):
    """GetDTO: 返回用户可切换的更多 Workspace 列表。"""
    rows = db.execute(text(
        "SELECT w.id, w.description FROM workspace w "
        "JOIN userdata u ON w.id = u.workspace_id "
        "WHERE u.login = :l"
    ), {"l": current_user.login}).fetchall()
    return [{"id": r[0], "description": r[1] or ""} for r in rows]


@router.get("/workspaces/reachable-users")
@router.get("/workspaces/reachable-users/", include_in_schema=False)
def reachable_users(db: Session = Depends(get_db),
                    current_user: Account = Depends(get_current_user)):
    """Payara 的 getReachableUsersForCaller。返回除当前用户外的所有账号。"""
    from app.models.auth import Account as Acct
    users = db.query(Acct).filter(Acct.login != current_user.login).all()
    return [{"login": u.login, "name": u.name, "email": u.email} for u in users]


@router.get("/workspaces/{ws}/stats-overview")
@router.get("/workspaces/{ws}/stats-overview/", include_in_schema=False)
def stats_overview(ws: str, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    # Payara 对齐: 统计有至少一个迭代的零件/文档（不限签入状态）
    parts = db.execute(text(
        "SELECT COUNT(DISTINCT pm.partnumber) FROM partmaster pm "
        "JOIN partrevision pr ON pm.workspace_id=pr.workspace_id AND pm.partnumber=pr.partmaster_partnumber "
        "JOIN partiteration pi ON pr.workspace_id=pi.workspace_id AND pr.partmaster_partnumber=pi.partmaster_partnumber AND pr.version=pi.partrevision_version "
        "WHERE pm.workspace_id=:w"
    ), {"w": ws}).scalar() or 0
    docs = db.execute(text(
        "SELECT COUNT(DISTINCT dm.id) FROM documentmaster dm "
        "JOIN documentrevision dr ON dm.workspace_id=dr.workspace_id AND dm.id=dr.documentmaster_id "
        "JOIN documentiteration di ON dr.workspace_id=di.workspace_id AND dr.documentmaster_id=di.documentmaster_id AND dr.version=di.documentrevision_version "
        "WHERE dm.workspace_id=:w"
    ), {"w": ws}).scalar() or 0
    users = db.execute(text("SELECT COUNT(*) FROM userdata WHERE workspace_id=:w"), {"w": ws}).scalar() or 0
    products = db.execute(text("SELECT COUNT(*) FROM configurationitem WHERE workspace_id=:w"), {"w": ws}).scalar() or 0
    checked_out_docs = db.execute(text(
        "SELECT COUNT(*) FROM documentrevision WHERE workspace_id=:w AND checkoutuser_login IS NOT NULL"
    ), {"w": ws}).scalar() or 0
    checked_out_parts = db.execute(text(
        "SELECT COUNT(*) FROM partrevision WHERE workspace_id=:w AND checkoutuser_login IS NOT NULL"
    ), {"w": ws}).scalar() or 0
    return {
        "parts": parts,
        "documents": docs,
        "users": users,
        "products": products,
        "checkedOutDocuments": checked_out_docs,
        "checkedOutParts": checked_out_parts,
    }


@router.get("/workspaces/{ws}/disk-usage")
@router.get("/workspaces/{ws}/disk-usage/", include_in_schema=False)
def disk_usage(ws: str, db: Session = Depends(get_db),
               current_user: Account = Depends(get_current_user)):
    return {"total": 0}


@router.get("/workspaces/{ws}/disk-usage-stats")
@router.get("/workspaces/{ws}/disk-usage-stats/", include_in_schema=False)
def disk_usage_stats(ws: str, db: Session = Depends(get_db),
                     current_user: Account = Depends(get_current_user)):
    vault = Path(settings.VAULT_PATH) / ws
    total = 0
    parts_size = 0
    docs_size = 0
    if vault.exists():
        for p in vault.rglob("*"):
            if p.is_file():
                size = p.stat().st_size
                total += size
                if "/parts/" in str(p):
                    parts_size += size
                elif "/documents/" in str(p):
                    docs_size += size
    return {"documents": docs_size, "parts": parts_size,
            "partTemplates": 0, "documentTemplates": 0}


@router.get("/workspaces/{ws}/checked-out-documents-stats")
@router.get("/workspaces/{ws}/checked-out-documents-stats/", include_in_schema=False)
def checked_out_docs_stats(ws: str, db: Session = Depends(get_db),
                           current_user: Account = Depends(get_current_user)):
    from sqlalchemy import text
    from datetime import datetime
    rows = db.execute(text(
        "SELECT checkoutuser_login, checkoutdate "
        "FROM documentrevision "
        "WHERE workspace_id = :ws AND checkoutuser_login IS NOT NULL"
    ), {"ws": ws}).fetchall()
    result = {}
    for r in rows:
        login = r[0] or "unknown"
        ts = int(r[1].timestamp() * 1000) if r[1] else 0
        if login not in result:
            result[login] = []
        result[login].append({"date": ts})
    return result


@router.get("/workspaces/{ws}/checked-out-parts-stats")
@router.get("/workspaces/{ws}/checked-out-parts-stats/", include_in_schema=False)
def checked_out_parts_stats(ws: str, db: Session = Depends(get_db),
                            current_user: Account = Depends(get_current_user)):
    from sqlalchemy import text
    from datetime import datetime
    rows = db.execute(text(
        "SELECT checkoutuser_login, checkoutdate "
        "FROM partrevision "
        "WHERE workspace_id = :ws AND checkoutuser_login IS NOT NULL"
    ), {"ws": ws}).fetchall()
    result = {}
    for r in rows:
        login = r[0] or "unknown"
        ts = int(r[1].timestamp() * 1000) if r[1] else 0
        if login not in result:
            result[login] = []
        result[login].append({"date": ts})
    return result


@router.get("/workspaces/{ws}/front-options")
@router.get("/workspaces/{ws}/front-options/", include_in_schema=False)
def front_options(ws: str, db: Session = Depends(get_db),
                  current_user: Account = Depends(get_current_user)):
    part_cols = db.execute(text(
        "SELECT tablecolumn FROM workspace_parttablecolumn "
        "WHERE workspace_id = :ws ORDER BY partcolumn_order"
    ), {"ws": ws}).fetchall()
    doc_cols = db.execute(text(
        "SELECT tablecolumn FROM workspace_documenttablecolumn "
        "WHERE workspace_id = :ws ORDER BY documentcolumn_order"
    ), {"ws": ws}).fetchall()
    return {
        "documentTableColumns": [r[0] for r in doc_cols],
        "partTableColumns": [r[0] for r in part_cols],
    }


@router.put("/workspaces/{ws}/front-options")
@router.put("/workspaces/{ws}/front-options/", include_in_schema=False)
def save_front_options(ws: str, body: dict, db: Session = Depends(get_db),
                       current_user: Account = Depends(get_current_user)):
    existing = db.execute(text(
        "SELECT workspace_id FROM workspacefrontoptions WHERE workspace_id = :ws"
    ), {"ws": ws}).fetchone()
    if not existing:
        db.execute(text(
            "INSERT INTO workspacefrontoptions (workspace_id) VALUES (:ws)"
        ), {"ws": ws})

    db.execute(text(
        "DELETE FROM workspace_parttablecolumn WHERE workspace_id = :ws"
    ), {"ws": ws})
    db.execute(text(
        "DELETE FROM workspace_documenttablecolumn WHERE workspace_id = :ws"
    ), {"ws": ws})

    for i, col in enumerate(body.get("partTableColumns", [])):
        db.execute(text(
            "INSERT INTO workspace_parttablecolumn (workspace_id, tablecolumn, partcolumn_order) "
            "VALUES (:ws, :col, :ord)"
        ), {"ws": ws, "col": col, "ord": i})

    for i, col in enumerate(body.get("documentTableColumns", [])):
        db.execute(text(
            "INSERT INTO workspace_documenttablecolumn (workspace_id, tablecolumn, documentcolumn_order) "
            "VALUES (:ws, :col, :ord)"
        ), {"ws": ws, "col": col, "ord": i})

    db.commit()
    return Response(status_code=204)


@router.get("/workspaces/{ws}/back-options")
@router.get("/workspaces/{ws}/back-options/", include_in_schema=False)
def back_options(ws: str, db: Session = Depends(get_db),
                  current_user: Account = Depends(get_current_user)):
    return {"sendEmails": False, "workspaceId": ws}


@router.get("/workspaces/{ws}/tags")
@router.get("/workspaces/{ws}/tags/", include_in_schema=False)
def workspace_tags(ws: str, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    try:
        rows = db.execute(text(
            "SELECT DISTINCT label FROM tag WHERE workspace_id = :ws ORDER BY label"
        ), {"ws": ws}).fetchall()
        return [{"id": r[0], "label": r[0], "workspaceId": ws} for r in rows]
    except Exception:
        return []


@router.get("/workspaces/{ws}/tags/{tag_id}/documents")
@router.get("/workspaces/{ws}/tags/{tag_id}/documents/", include_in_schema=False)
def tag_documents(ws: str, tag_id: str, db: Session = Depends(get_db),
                  current_user: Account = Depends(get_current_user)):
    return []


@router.get("/workspaces/{ws}/lov")
@router.get("/workspaces/{ws}/lov/", include_in_schema=False)
def list_of_values(ws: str, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    try:
        return []
    except Exception:
        return []


@router.get("/workspaces/{ws}/attributes/part-iterations")
@router.get("/workspaces/{ws}/attributes/part-iterations/", include_in_schema=False)
def attributes_part_iterations(ws: str, db: Session = Depends(get_db),
                               current_user: Account = Depends(get_current_user)):
    try:
        return []
    except Exception:
        return []


@router.get("/workspaces/{ws}/attributes/path-data")
@router.get("/workspaces/{ws}/attributes/path-data/", include_in_schema=False)
def attributes_path_data(ws: str, db: Session = Depends(get_db),
                         current_user: Account = Depends(get_current_user)):
    try:
        return []
    except Exception:
        return []


@router.get("/workspaces/{ws}")
@router.get("/workspaces/{ws}/", include_in_schema=False)
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

