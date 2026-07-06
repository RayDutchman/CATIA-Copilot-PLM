"""工作区 CRUD 端点。"""
from typing import Dict, List
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import (
    AccessRightException, EntityAlreadyExistsException,
    EntityNotFoundException, NotAllowedException,
    WorkspaceNotFoundException,
)
from app.models.auth import Account
from app.schemas.admin import (
    WorkspaceDTO, WorkspaceListDTO, StatsOverviewDTO, DiskUsageDTO,
    FrontOptionsDTO, BackOptionsDTO, ReachableUserDTO,
)
from app.schemas.misc import TagDTO, LOVDTO, LOVValueDTO

router = APIRouter(prefix="/docdoku-plm-server-rest/api")


def _check_workspace_admin(db: Session, ws: str, current_user: Account):
    """验证当前用户是全局管理员或工作区管理员，否则 403。"""
    is_global_admin = db.execute(text(
        "SELECT 1 FROM usergroupmapping WHERE login=:l AND groupname='admin'"
    ), {"l": current_user.login}).first()
    if is_global_admin:
        return
    is_ws_admin = db.execute(text(
        "SELECT 1 FROM workspace WHERE id=:w AND admin_login=:l"
    ), {"w": ws, "l": current_user.login}).first()
    if not is_ws_admin:
        raise AccessRightException("AccessRightException")


def _row_to_dict(r) -> dict:
    return {
        "id": r[0],
        "description": r[1] or "",
        "enabled": bool(r[2]) if r[2] is not None else True,
        "folderLocked": bool(r[3]) if r[3] is not None else False,
        "admin": r[4] or "",
        "creationDate": None,
    }


@router.get("/workspaces", response_model=WorkspaceListDTO)
@router.get("/workspaces/", include_in_schema=False)
def list_workspaces(db: Session = Depends(get_db),
                    current_user: Account = Depends(get_current_user)):
    rows = db.execute(text(
        "SELECT id, description, enabled, folderlocked, admin_login FROM workspace ORDER BY id"
    )).fetchall()
    all_ws = [_row_to_dict(r) for r in rows]

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


@router.get("/workspaces/more", response_model=List[WorkspaceDTO])
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


@router.get("/workspaces/reachable-users", response_model=List[ReachableUserDTO])
@router.get("/workspaces/reachable-users/", include_in_schema=False)
def reachable_users(db: Session = Depends(get_db),
                    current_user: Account = Depends(get_current_user)):
    """Payara 的 getReachableUsersForCaller。返回除当前用户外的所有账号。"""
    from app.models.auth import Account as Acct
    users = db.query(Acct).filter(Acct.login != current_user.login).all()
    return [{"login": u.login, "name": u.name, "email": u.email} for u in users]


@router.get("/workspaces/{ws}/stats-overview", response_model=StatsOverviewDTO)
@router.get("/workspaces/{ws}/stats-overview/", include_in_schema=False)
def stats_overview(ws: str, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    # 对齐 Payara: 直接 COUNT PartRevision/DocumentRevision 行数
    parts = db.execute(text(
        "SELECT COUNT(*) FROM partrevision WHERE workspace_id=:w"), {"w": ws}).scalar() or 0
    docs = db.execute(text(
        "SELECT COUNT(*) FROM documentrevision WHERE workspace_id=:w"), {"w": ws}).scalar() or 0
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


@router.get("/workspaces/{ws}/disk-usage", response_model=Dict[str, int])
@router.get("/workspaces/{ws}/disk-usage/", include_in_schema=False)
def disk_usage(ws: str, db: Session = Depends(get_db),
               current_user: Account = Depends(get_current_user)):
    return {"total": 0}


@router.get("/workspaces/{ws}/disk-usage-stats", response_model=DiskUsageDTO)
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


@router.get("/workspaces/{ws}/checked-out-documents-stats", response_model=Dict[str, List[dict]])
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


@router.get("/workspaces/{ws}/checked-out-parts-stats", response_model=Dict[str, List[dict]])
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


@router.get("/workspaces/{ws}/front-options", response_model=FrontOptionsDTO)
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
        "documentTableColumns": [r[0] for r in doc_cols] or [],
        "partTableColumns": [r[0] for r in part_cols] or _DEFAULT_PART_COLUMNS,
    }


# 默认列（对齐前端 part-table-columns.js defaultColumns）
_DEFAULT_PART_COLUMNS = ["pr.number", "pr.version", "pr.iteration", "pr.type", "pr.name", "pr.author"]


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


@router.get("/workspaces/{ws}/back-options", response_model=BackOptionsDTO)
@router.get("/workspaces/{ws}/back-options/", include_in_schema=False)
def back_options(ws: str, db: Session = Depends(get_db),
                  current_user: Account = Depends(get_current_user)):
    row = db.execute(text(
        "SELECT sendemails FROM workspacebackoptions WHERE workspace_id = :ws"
    ), {"ws": ws}).fetchone()
    send_emails = bool(row[0]) if row else False
    return {"sendEmails": send_emails, "workspaceId": ws}


@router.put("/workspaces/{ws}/back-options")
@router.put("/workspaces/{ws}/back-options/", include_in_schema=False)
def save_back_options(ws: str, body: dict, db: Session = Depends(get_db),
                      current_user: Account = Depends(get_current_user)):
    send_emails = body.get("sendEmails", False)
    existing = db.execute(text(
        "SELECT workspace_id FROM workspacebackoptions WHERE workspace_id = :ws"
    ), {"ws": ws}).fetchone()
    if existing:
        db.execute(text(
            "UPDATE workspacebackoptions SET sendemails = :se WHERE workspace_id = :ws"
        ), {"se": send_emails, "ws": ws})
    else:
        db.execute(text(
            "INSERT INTO workspacebackoptions (workspace_id, sendemails) VALUES (:ws, :se)"
        ), {"ws": ws, "se": send_emails})
    db.commit()
    return Response(status_code=204)


@router.put("/workspaces/{ws}/index", status_code=202, response_model=dict)
@router.put("/workspaces/{ws}/index/", status_code=202, include_in_schema=False)
def reindex_workspace(ws: str, db: Session = Depends(get_db),
                      current_user: Account = Depends(get_current_user)):
    return {"status": "accepted"}


@router.get("/workspaces/{ws}/tags", response_model=List[TagDTO])
@router.get("/workspaces/{ws}/tags/", include_in_schema=False)
def workspace_tags(ws: str, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    rows = db.execute(text(
        "SELECT label, workspace_id FROM tag WHERE workspace_id = :ws ORDER BY label"
    ), {"ws": ws}).fetchall()
    return [{"id": r[0], "label": r[0], "workspaceId": r[1]} for r in rows]


@router.post("/workspaces/{ws}/tags", status_code=201, response_model=TagDTO)
@router.post("/workspaces/{ws}/tags/", status_code=201, include_in_schema=False)
def create_tag(ws: str, body: dict, db: Session = Depends(get_db),
               current_user: Account = Depends(get_current_user)):
    label = body.get("label", "").strip()
    if not label:
        raise NotAllowedException("NotAllowedException9", "标签")
    existing = db.execute(text(
        "SELECT label FROM tag WHERE label = :label AND workspace_id = :ws"
    ), {"label": label, "ws": ws}).fetchone()
    if existing:
        raise EntityAlreadyExistsException("TagAlreadyExistsException", label)
    db.execute(text(
        "INSERT INTO tag (label, workspace_id) VALUES (:label, :ws)"
    ), {"label": label, "ws": ws})
    db.commit()
    return {"id": label, "label": label, "workspaceId": ws}


@router.post("/workspaces/{ws}/tags/multiple", status_code=201, response_model=List[TagDTO])
@router.post("/workspaces/{ws}/tags/multiple/", status_code=201, include_in_schema=False)
def create_tags_multiple(ws: str, body: dict, db: Session = Depends(get_db),
                         current_user: Account = Depends(get_current_user)):
    labels = body.get("tags", [])
    created = []
    for label in labels:
        label = str(label).strip()
        if not label:
            continue
        existing = db.execute(text(
            "SELECT label FROM tag WHERE label = :label AND workspace_id = :ws"
        ), {"label": label, "ws": ws}).fetchone()
        if existing:
            continue
        db.execute(text(
            "INSERT INTO tag (label, workspace_id) VALUES (:label, :ws)"
        ), {"label": label, "ws": ws})
        created.append({"id": label, "label": label, "workspaceId": ws})
    db.commit()
    return created


@router.delete("/workspaces/{ws}/tags/{tag_id}", status_code=204)
@router.delete("/workspaces/{ws}/tags/{tag_id}/", status_code=204, include_in_schema=False)
def delete_tag(ws: str, tag_id: str, db: Session = Depends(get_db),
               current_user: Account = Depends(get_current_user)):
    existing = db.execute(text(
        "SELECT label FROM tag WHERE label = :label AND workspace_id = :ws"
    ), {"label": tag_id, "ws": ws}).fetchone()
    if not existing:
        raise EntityNotFoundException("TagNotFoundException", tag_id)
    db.execute(text(
        "DELETE FROM tag WHERE label = :label AND workspace_id = :ws"
    ), {"label": tag_id, "ws": ws})
    db.commit()


@router.get("/workspaces/{ws}/tags/{tag_id}/documents", response_model=List[dict])
@router.get("/workspaces/{ws}/tags/{tag_id}/documents/", include_in_schema=False)
def tag_documents(ws: str, tag_id: str, db: Session = Depends(get_db),
                  current_user: Account = Depends(get_current_user)):
    return []


@router.get("/workspaces/{ws}/lov", response_model=Dict[str, List[LOVValueDTO]])
@router.get("/workspaces/{ws}/lov/", include_in_schema=False)
def list_of_values(ws: str, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    rows = db.execute(text(
        "SELECT l.name, l.workspace_id FROM lov l WHERE l.workspace_id = :ws ORDER BY l.name"
    ), {"ws": ws}).fetchall()
    result = {}
    for r in rows:
        name = r[0]
        nv_rows = db.execute(text(
            "SELECT nv.name, nv.value FROM lov_namevalue nv "
            "WHERE nv.lov_name = :name AND nv.lov_workspace_id = :ws "
            "ORDER BY nv.namevalue_order"
        ), {"name": name, "ws": ws}).fetchall()
        result[name] = [{"name": n[0], "value": n[1]} for n in nv_rows]
    return result


@router.post("/workspaces/{ws}/lov", status_code=201, response_model=LOVDTO)
@router.post("/workspaces/{ws}/lov/", status_code=201, include_in_schema=False)
def create_lov(ws: str, body: dict, db: Session = Depends(get_db),
               current_user: Account = Depends(get_current_user)):
    name = body.get("name", "").strip()
    if not name:
        raise NotAllowedException("NotAllowedException9", "名称")
    existing = db.execute(text(
        "SELECT name FROM lov WHERE name = :name AND workspace_id = :ws"
    ), {"name": name, "ws": ws}).fetchone()
    if existing:
        raise EntityAlreadyExistsException("LOVAlreadyExistsException", name)
    db.execute(text(
        "INSERT INTO lov (name, workspace_id) VALUES (:name, :ws)"
    ), {"name": name, "ws": ws})
    values = body.get("values", [])
    for i, v in enumerate(values):
        db.execute(text(
            "INSERT INTO lov_namevalue (name, value, lov_name, lov_workspace_id, namevalue_order) "
            "VALUES (:name, :value, :lov_name, :ws, :ord)"
        ), {"name": v.get("name", ""), "value": v.get("value", ""),
            "lov_name": name, "ws": ws, "ord": i})
    db.commit()
    return {"name": name, "workspaceId": ws, "values": values}


@router.put("/workspaces/{ws}/lov/{name}", response_model=LOVDTO)
@router.put("/workspaces/{ws}/lov/{name}/", include_in_schema=False)
def update_lov(ws: str, name: str, body: dict, db: Session = Depends(get_db),
               current_user: Account = Depends(get_current_user)):
    existing = db.execute(text(
        "SELECT name FROM lov WHERE name = :name AND workspace_id = :ws"
    ), {"name": name, "ws": ws}).fetchone()
    if not existing:
        raise EntityNotFoundException("LOVNotFoundException", name)
    db.execute(text(
        "DELETE FROM lov_namevalue WHERE lov_name = :name AND lov_workspace_id = :ws"
    ), {"name": name, "ws": ws})
    values = body.get("values", [])
    for i, v in enumerate(values):
        db.execute(text(
            "INSERT INTO lov_namevalue (name, value, lov_name, lov_workspace_id, namevalue_order) "
            "VALUES (:name, :value, :lov_name, :ws, :ord)"
        ), {"name": v.get("name", ""), "value": v.get("value", ""),
            "lov_name": name, "ws": ws, "ord": i})
    db.commit()
    return {"name": name, "workspaceId": ws, "values": values}


@router.delete("/workspaces/{ws}/lov/{name}", status_code=204)
@router.delete("/workspaces/{ws}/lov/{name}/", status_code=204, include_in_schema=False)
def delete_lov(ws: str, name: str, db: Session = Depends(get_db),
               current_user: Account = Depends(get_current_user)):
    existing = db.execute(text(
        "SELECT name FROM lov WHERE name = :name AND workspace_id = :ws"
    ), {"name": name, "ws": ws}).fetchone()
    if not existing:
        raise EntityNotFoundException("LOVNotFoundException", name)
    db.execute(text(
        "DELETE FROM lov_namevalue WHERE lov_name = :name AND lov_workspace_id = :ws"
    ), {"name": name, "ws": ws})
    db.execute(text(
        "DELETE FROM lov WHERE name = :name AND workspace_id = :ws"
    ), {"name": name, "ws": ws})
    db.commit()


@router.get("/workspaces/{ws}/attributes/part-iterations", response_model=List[str])
@router.get("/workspaces/{ws}/attributes/part-iterations/", include_in_schema=False)
def attributes_part_iterations(ws: str, db: Session = Depends(get_db),
                               current_user: Account = Depends(get_current_user)):
    rows = db.execute(text(
        "SELECT DISTINCT ia.name FROM partiteration_attribute pia "
        "JOIN instanceattribute ia ON ia.id = pia.instanceattribute_id "
        "WHERE pia.workspace_id = :ws ORDER BY ia.name"
    ), {"ws": ws}).fetchall()
    return [r[0] for r in rows]


@router.get("/workspaces/{ws}/attributes/path-data", response_model=List[str])
@router.get("/workspaces/{ws}/attributes/path-data/", include_in_schema=False)
def attributes_path_data(ws: str, db: Session = Depends(get_db),
                         current_user: Account = Depends(get_current_user)):
    rows = db.execute(text(
        "SELECT DISTINCT iat.name FROM partiteration_pathdata_attr ppa "
        "JOIN instanceattributetemplate iat ON iat.id = ppa.instanceattribute_template_id "
        "WHERE ppa.workspace_id = :ws ORDER BY iat.name"
    ), {"ws": ws}).fetchall()
    return [r[0] for r in rows]


@router.get("/workspaces/{ws}", response_model=WorkspaceDTO)
@router.get("/workspaces/{ws}/", include_in_schema=False)
def get_workspace(ws: str, db: Session = Depends(get_db),
                  current_user: Account = Depends(get_current_user)):
    r = db.execute(text(
        "SELECT id, description, enabled, folderlocked, admin_login "
        "FROM workspace WHERE id = :id"
    ), {"id": ws}).fetchone()
    if not r:
        raise WorkspaceNotFoundException("WorkspaceNotFoundException", ws)
    return _row_to_dict(r)


@router.post("/workspaces", status_code=201, response_model=WorkspaceDTO)
@router.post("/workspaces/", status_code=201, include_in_schema=False)
def create_workspace(body: dict, db: Session = Depends(get_db),
                     current_user: Account = Depends(get_current_user),
                     userLogin: str = Query(None)):
    # 检查平台策略：ADMIN_VALIDATION 时仅管理员可创建
    strategy_row = db.execute(text(
        "SELECT workspacecreationstrategy FROM platformoptions LIMIT 1"
    )).first()
    if strategy_row and strategy_row[0] == 1:  # ADMIN_VALIDATION
        is_admin = db.execute(text(
            "SELECT 1 FROM usergroupmapping WHERE login=:l AND groupname='admin'"
        ), {"l": current_user.login}).first()
        if not is_admin:
            raise AccessRightException("AccessRightException")
    ws_id = body.get("id", "").strip()
    if not ws_id:
        raise NotAllowedException("NotAllowedException9")

    existing = db.execute(text(
        "SELECT id FROM workspace WHERE id = :id"
    ), {"id": ws_id}).fetchone()
    if existing:
        raise EntityAlreadyExistsException("WorkspaceAlreadyExistsException", ws_id)

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


@router.put("/workspaces/{ws}", response_model=WorkspaceDTO)
@router.put("/workspaces/{ws}/", include_in_schema=False)
def update_workspace(ws: str, body: dict, db: Session = Depends(get_db),
                     current_user: Account = Depends(get_current_user)):
    existing = db.execute(text(
        "SELECT id FROM workspace WHERE id = :id"
    ), {"id": ws}).fetchone()
    if not existing:
        raise WorkspaceNotFoundException("WorkspaceNotFoundException", ws)

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


@router.put("/workspaces/{ws}/admin", response_model=WorkspaceDTO)
@router.put("/workspaces/{ws}/admin/", include_in_schema=False)
def change_admin(ws: str, body: dict, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    """更换工作区管理员。仅全局管理员或当前工作区管理员可操作。"""
    _check_workspace_admin(db, ws, current_user)
    new_admin = body.get("login", "").strip()
    if not new_admin:
        raise NotAllowedException("NotAllowedException9")
    # 验证新管理员是工作区成员
    member = db.execute(text(
        "SELECT 1 FROM userdata WHERE login = :l AND workspace_id = :ws"
    ), {"l": new_admin, "ws": ws}).first()
    if not member:
        raise NotAllowedException("NotAllowedException9", "login")
    db.execute(text(
        "UPDATE workspace SET admin_login = :a WHERE id = :ws"
    ), {"a": new_admin, "ws": ws})
    db.commit()
    r = db.execute(text(
        "SELECT id, description, enabled, folderlocked, admin_login "
        "FROM workspace WHERE id = :id"
    ), {"id": ws}).fetchone()
    return _row_to_dict(r)


@router.delete("/workspaces/{ws}", status_code=204)
def delete_workspace(ws: str, db: Session = Depends(get_db),
                     current_user: Account = Depends(get_current_user)):
    _check_workspace_admin(db, ws, current_user)
    existing = db.execute(text(
        "SELECT id FROM workspace WHERE id = :id"
    ), {"id": ws}).fetchone()
    if not existing:
        raise WorkspaceNotFoundException("WorkspaceNotFoundException", ws)

    # 级联删除：按依赖顺序从子到父
    # 1. 零件相关 join 表
    db.execute(text("DELETE FROM partiteration_binres WHERE workspace_id=:ws"), {"ws": ws})
    db.execute(text("DELETE FROM partiteration_geometry WHERE workspace_id=:ws"), {"ws": ws})
    db.execute(text("DELETE FROM partiteration_partusagelink WHERE workspace_id=:ws"), {"ws": ws})
    db.execute(text("DELETE FROM partrevision_tag WHERE partmaster_workspace_id=:ws"), {"ws": ws})

    # 2. 文档相关 join 表
    db.execute(text("DELETE FROM documentiteration_binres WHERE workspace_id=:ws"), {"ws": ws})
    db.execute(text("DELETE FROM documentrevision_tag WHERE documentmaster_workspace_id=:ws"), {"ws": ws})

    # 3. 转换任务
    db.execute(text("DELETE FROM conversion WHERE workspace_id=:ws"), {"ws": ws})

    # 4. 零件迭代 → 版本 → 主数据
    db.execute(text("DELETE FROM partiteration WHERE workspace_id=:ws"), {"ws": ws})
    db.execute(text("DELETE FROM partrevision WHERE workspace_id=:ws"), {"ws": ws})
    db.execute(text("DELETE FROM partmaster WHERE workspace_id=:ws"), {"ws": ws})

    # 5. 文档迭代 → 版本 → 主数据
    db.execute(text("DELETE FROM documentiteration WHERE workspace_id=:ws"), {"ws": ws})
    db.execute(text("DELETE FROM documentrevision WHERE workspace_id=:ws"), {"ws": ws})
    db.execute(text("DELETE FROM documentmaster WHERE workspace_id=:ws"), {"ws": ws})
    db.execute(text("DELETE FROM documentmastertemplate WHERE workspace_id=:ws"), {"ws": ws})

    # 6. 产品配置项
    db.execute(text("DELETE FROM productinstanceiteration WHERE workspace_id=:ws"), {"ws": ws})
    db.execute(text("DELETE FROM productinstancemaster WHERE workspace_id=:ws"), {"ws": ws})
    db.execute(text("DELETE FROM productbaseline WHERE configurationitem_workspace_id=:ws"), {"ws": ws})
    db.execute(text("DELETE FROM productconfiguration WHERE configurationitem_workspace_id=:ws"), {"ws": ws})
    db.execute(text("DELETE FROM configurationitem WHERE workspace_id=:ws"), {"ws": ws})

    # 7. 角色与 ACL
    db.execute(text("DELETE FROM role_user WHERE role_workspace_id=:ws OR user_workspace_id=:ws"), {"ws": ws})
    db.execute(text("DELETE FROM role_usergroup WHERE role_workspace_id=:ws OR usergroup_workspace_id=:ws"), {"ws": ws})
    db.execute(text("DELETE FROM role WHERE workspace_id=:ws"), {"ws": ws})
    db.execute(text("DELETE FROM acluserentry WHERE principal_workspace_id=:ws"), {"ws": ws})
    db.execute(text("DELETE FROM aclusergroupentry WHERE principal_workspace_id=:ws"), {"ws": ws})

    # 8. 用户/组关系
    db.execute(text("DELETE FROM workspaceusermembership WHERE workspace_id=:ws"), {"ws": ws})
    db.execute(text("DELETE FROM workspaceusergroupmembership WHERE workspace_id=:ws"), {"ws": ws})
    db.execute(text("DELETE FROM usergroup WHERE workspace_id=:ws"), {"ws": ws})

    # 9. 用户数据与全局组映射（仅当用户不在其他工作区时清理 usergroupmapping）
    users = db.execute(text("SELECT login FROM userdata WHERE workspace_id=:ws"), {"ws": ws}).fetchall()
    db.execute(text("DELETE FROM userdata WHERE workspace_id=:ws"), {"ws": ws})
    for (login,) in users:
        remaining = db.execute(text(
            "SELECT COUNT(*) FROM userdata WHERE login=:l"
        ), {"l": login}).scalar()
        if remaining == 0:
            db.execute(text("DELETE FROM usergroupmapping WHERE login=:l"), {"l": login})

    # 10. 工作区自身
    db.execute(text("DELETE FROM workspace WHERE id = :id"), {"id": ws})
    db.commit()

