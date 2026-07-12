"""工作区 CRUD 端点。"""
from pathlib import Path
from typing import Dict, List
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
    TagAlreadyExistsException, TagNotFoundException,
    WorkspaceNotFoundException, ListOfValuesNotFoundException,
)
from app.models.auth import Account
from app.models.util.naming_convention import is_valid_name
from app.schemas.admin import (
    WorkspaceDTO, WorkspaceListDTO, StatsOverviewDTO, DiskUsageDTO,
    FrontOptionsDTO, BackOptionsDTO,
)
from app.schemas.misc import TagDTO, LOVDTO, LOVValueDTO
from app.schemas.part import UserDTO
from app.services.indexer_manager import indexer_manager
from app.services.workspace_manager import workspace_service
from app.services.workspace_deletion import cascade_delete_workspace

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
        raise AccessRightException("AccessRightException", current_user.login)


def _row_to_dict(r) -> dict:
    return {
        "id": r[0],
        "description": r[1] or "",
        "enabled": bool(r[2]) if r[2] is not None else True,
        "folderLocked": bool(r[3]) if r[3] is not None else False,
        "admin": r[4] or "",
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


@router.get("/workspaces/reachable-users", response_model=List[UserDTO])
@router.get("/workspaces/reachable-users/", include_in_schema=False)
def reachable_users(db: Session = Depends(get_db),
                    current_user: Account = Depends(get_current_user)):
    """返回与当前用户有共同工作区的其他用户。对齐 Java WorkspaceResource.getReachableUsersForCaller → UserDTO[]"""
    from app.models.auth import Account as Acct
    caller_ws = db.execute(text(
        "SELECT workspace_id FROM userdata WHERE login = :l"
    ), {"l": current_user.login}).fetchall()
    ws_ids = [r[0] for r in caller_ws]
    if not ws_ids:
        return []
    user_logins = db.execute(text(
        "SELECT DISTINCT u.login FROM userdata u "
        "WHERE u.workspace_id = ANY(:ws) AND u.login != :caller"
    ), {"ws": ws_ids, "caller": current_user.login}).fetchall()
    logins = [r[0] for r in user_logins]
    if not logins:
        return []
    users = db.query(Acct).filter(Acct.login.in_(logins)).all()
    login_to_user = {u.login: u for u in users}
    ud_rows = db.execute(text(
        "SELECT login, workspace_id FROM userdata WHERE login = ANY(:logins) AND workspace_id = ANY(:ws)"
    ), {"logins": logins, "ws": ws_ids}).fetchall()
    login_to_ws = {}
    for r in ud_rows:
        if r[0] not in login_to_ws:
            login_to_ws[r[0]] = r[1]
    result = []
    for login in logins:
        u = login_to_user.get(login)
        if u:
            result.append({
                "login": u.login,
                "name": u.name,
                "email": u.email,
                "language": u.language or "",
                "workspaceId": login_to_ws.get(login, ""),
            })
    return result


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
    return workspace_service.get_workspace_front_options(db, ws)


@router.put("/workspaces/{ws}/front-options")
@router.put("/workspaces/{ws}/front-options/", include_in_schema=False)
def save_front_options(ws: str, body: dict, db: Session = Depends(get_db),
                       current_user: Account = Depends(get_current_user)):
    workspace_service.update_workspace_front_options(db, ws, body)
    return Response(status_code=204)


@router.get("/workspaces/{ws}/back-options", response_model=BackOptionsDTO)
@router.get("/workspaces/{ws}/back-options/", include_in_schema=False)
def back_options(ws: str, db: Session = Depends(get_db),
                  current_user: Account = Depends(get_current_user)):
    return workspace_service.get_workspace_back_options(db, ws)


@router.put("/workspaces/{ws}/back-options")
@router.put("/workspaces/{ws}/back-options/", include_in_schema=False)
def save_back_options(ws: str, body: dict, db: Session = Depends(get_db),
                      current_user: Account = Depends(get_current_user)):
    workspace_service.update_workspace_back_options(db, ws, body)
    return Response(status_code=204)


@router.put("/workspaces/{ws}/index", status_code=202, response_model=dict)
@router.put("/workspaces/{ws}/index/", status_code=202, include_in_schema=False)
def reindex_workspace(ws: str, db: Session = Depends(get_db),
                      current_user: Account = Depends(get_current_user)):
    result = indexer_manager.reindex_all(db, ws, current_user, check_admin=True)
    return result



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
        raise NotAllowedException("NotAllowedException9", name)
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
        raise ListOfValuesNotFoundException("ListOfValuesNotFoundException", name)
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
        raise ListOfValuesNotFoundException("ListOfValuesNotFoundException", name)
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
    # 检查平台策略：ADMIN_VALIDATION 时仅管理员可创建，且 workspace 默认 disabled
    strategy_row = db.execute(text(
        "SELECT workspacecreationstrategy FROM platformoptions LIMIT 1"
    )).first()
    is_admin_validation = strategy_row is not None and strategy_row[0] == 1
    if is_admin_validation:
        is_admin = db.execute(text(
            "SELECT 1 FROM usergroupmapping WHERE login=:l AND groupname='admin'"
        ), {"l": current_user.login}).first()
        if not is_admin:
            raise AccessRightException("AccessRightException", current_user.login)
    ws_id = body.get("id", "").strip()
    if not ws_id:
        raise NotAllowedException("NotAllowedException9", ws_id)

    # 命名约定校验（对齐 Java WorkspaceManagerBean.createWorkspace）
    if not is_valid_name(ws_id):
        raise NotAllowedException("NotAllowedException9", ws_id)

    existing = db.execute(text(
        "SELECT id FROM workspace WHERE id = :id"
    ), {"id": ws_id}).fetchone()
    if existing:
        raise EntityAlreadyExistsException("WorkspaceAlreadyExistsException", ws_id)

    admin = userLogin or current_user.login
    desc = body.get("description", "")
    folder_locked = body.get("folderLocked", False)
    enabled = not is_admin_validation  # ADMIN_VALIDATION → false，否则 true

    db.execute(text(
        "INSERT INTO workspace (id, description, enabled, folderlocked, admin_login) "
        "VALUES (:id, :desc, :enabled, :folder_locked, :admin)"
    ), {"id": ws_id, "desc": desc, "enabled": enabled,
        "folder_locked": folder_locked, "admin": admin})

    # Payara 对齐: createWorkspace → createUser + addUserMembership
    db.execute(text(
        "INSERT INTO userdata (login, workspace_id) VALUES (:login, :ws)"
    ), {"login": admin, "ws": ws_id})
    db.execute(text(
        "INSERT INTO workspaceusermembership "
        "(workspace_id, member_login, member_workspace_id) "
        "VALUES (:ws, :login, :ws) "
        "ON CONFLICT DO NOTHING"
    ), {"ws": ws_id, "login": admin})
    db.commit()

    indexer_manager.create_index(ws_id)  # 对标 createWorkspace:157

    return {
        "id": ws_id,
        "description": desc,
        "enabled": enabled,
        "folderLocked": folder_locked,
        "admin": admin,
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
        raise NotAllowedException("NotAllowedException9", new_admin)
    # 验证新管理员是工作区成员
    member = db.execute(text(
        "SELECT 1 FROM userdata WHERE login = :l AND workspace_id = :ws"
    ), {"l": new_admin, "ws": ws}).first()
    if not member:
        raise NotAllowedException("NotAllowedException9", new_admin)
    db.execute(text(
        "UPDATE workspace SET admin_login = :a WHERE id = :ws"
    ), {"a": new_admin, "ws": ws})
    db.commit()
    r = db.execute(text(
        "SELECT id, description, enabled, folderlocked, admin_login "
        "FROM workspace WHERE id = :id"
    ), {"id": ws}).fetchone()
    return _row_to_dict(r)


@router.delete("/workspaces/{ws}", status_code=202)
def delete_workspace(ws: str, db: Session = Depends(get_db),
                     current_user: Account = Depends(get_current_user)):
    _check_workspace_admin(db, ws, current_user)
    existing = db.execute(text(
        "SELECT id FROM workspace WHERE id = :id"
    ), {"id": ws}).fetchone()
    if not existing:
        raise WorkspaceNotFoundException("WorkspaceNotFoundException", ws)
    cascade_delete_workspace(db, ws)
