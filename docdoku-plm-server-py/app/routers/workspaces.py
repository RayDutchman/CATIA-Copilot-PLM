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
    TagAlreadyExistsException, TagNotFoundException,
    WorkspaceNotFoundException, ListOfValuesNotFoundException,
)
from app.models.auth import Account
from app.schemas.admin import (
    WorkspaceDTO, WorkspaceListDTO, StatsOverviewDTO, DiskUsageDTO,
    FrontOptionsDTO, BackOptionsDTO, ReachableUserDTO,
)
from app.schemas.misc import TagDTO, LOVDTO, LOVValueDTO
from app.services.indexer_manager import indexer_manager
from app.services.workspace_manager import workspace_service

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
    """返回与当前用户有共同工作区的其他用户。"""
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
        raise NotAllowedException("NotAllowedException9", label)
    existing = db.execute(text(
        "SELECT label FROM tag WHERE label = :label AND workspace_id = :ws"
    ), {"label": label, "ws": ws}).fetchone()
    if existing:
        raise TagAlreadyExistsException("TagAlreadyExistsException", label)
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
        raise TagNotFoundException("TagNotFoundException", tag_id)
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
    # 检查平台策略：ADMIN_VALIDATION 时仅管理员可创建
    strategy_row = db.execute(text(
        "SELECT workspacecreationstrategy FROM platformoptions LIMIT 1"
    )).first()
    if strategy_row and strategy_row[0] == 1:  # ADMIN_VALIDATION
        is_admin = db.execute(text(
            "SELECT 1 FROM usergroupmapping WHERE login=:l AND groupname='admin'"
        ), {"l": current_user.login}).first()
        if not is_admin:
            raise AccessRightException("AccessRightException", current_user.login)
    ws_id = body.get("id", "").strip()
    if not ws_id:
        raise NotAllowedException("NotAllowedException9", ws_id)

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


@router.delete("/workspaces/{ws}", status_code=204)
def delete_workspace(ws: str, db: Session = Depends(get_db),
                     current_user: Account = Depends(get_current_user)):
    _check_workspace_admin(db, ws, current_user)
    existing = db.execute(text(
        "SELECT id FROM workspace WHERE id = :id"
    ), {"id": ws}).fetchone()
    if not existing:
        raise WorkspaceNotFoundException("WorkspaceNotFoundException", ws)

    indexer_manager.delete_index(ws)  # 对标 deleteWorkspace:103

    # 完整级联删除（对齐 WorkspaceDAO.removeWorkspace + JPA cascade），
    # SET LOCAL session_replication_role='replica' 关闭 FK 触发器，避免严格删除顺序要求；
    # 但仍按从叶到根的顺序删除，确保稳定性。
    db.execute(text("SET LOCAL session_replication_role='replica'"))

    # ── 0. 预先捕获未按 workspace 列定位的叶子表 ID ──
    # workflow 实例（partrevision.workflow_id / documentrevision.workflow_id / workspace_workflow）
    wf_rows = db.execute(text(
        "SELECT wf.id FROM workflow wf WHERE id IN ("
        "  SELECT workflow_id FROM partrevision WHERE workspace_id=:ws AND workflow_id IS NOT NULL UNION "
        "  SELECT workflow_id FROM documentrevision WHERE workspace_id=:ws AND workflow_id IS NOT NULL UNION "
        "  SELECT workflow_id FROM workspace_workflow WHERE workspace_id=:ws UNION "
        "  SELECT workflow_id FROM part_aborted_workflow WHERE partmaster_workspace_id=:ws UNION "
        "  SELECT workflow_id FROM document_aborted_workflow WHERE documentmaster_workspace_id=:ws)"
    ), {"ws": ws}).fetchall()
    wf_ids = [r[0] for r in wf_rows]

    # workflowmodel（workspace_id 外键）
    wfm_rows = db.execute(text(
        "SELECT id FROM workflowmodel WHERE workspace_id=:ws"
    ), {"ws": ws}).fetchall()
    wfm_ids = [r[0] for r in wfm_rows]

    # pathdatamaster（通过 prdinstiteration_pathdatamstr 定位）
    pdm_rows = db.execute(text(
        "SELECT pm.id FROM pathdatamaster pm JOIN prdinstiteration_pathdatamstr lk "
        "ON lk.pathdatamaster_id=pm.id WHERE lk.workspace_id=:ws"
    ), {"ws": ws}).fetchall()
    pdm_ids = [r[0] for r in pdm_rows]

    # pathtopathlink（通过 configurationitem_p2plink / productbaseline_p2plink / prdinstiteration_p2plink）
    ptl_rows = db.execute(text(
        "SELECT id FROM pathtopathlink WHERE id IN ("
        "  SELECT pathtopathlink_id FROM configurationitem_p2plink WHERE workspace_id=:ws UNION "
        "  SELECT pathtopathlink_id FROM productbaseline_p2plink p2 JOIN productbaseline pb "
        "    ON pb.id=p2.productbaseline_id WHERE pb.configurationitem_workspace_id=:ws UNION "
        "  SELECT pathtopathlink_id FROM prdinstiteration_p2plink WHERE workspace_id=:ws)"
    ), {"ws": ws}).fetchall()
    ptl_ids = [r[0] for r in ptl_rows]

    # instanceattribute（通过 5 个 join 表 + InstancePartNumberAttribute）
    ia_rows = db.execute(text(
        "SELECT ia.id FROM instanceattribute ia WHERE ia.id IN ("
        "  SELECT instanceattribute_id FROM partiteration_attribute WHERE workspace_id=:ws UNION "
        "  SELECT instanceattribute_id FROM documentiteration_attribute WHERE workspace_id=:ws UNION "
        "  SELECT instanceattribute_id FROM pathdataiteration_attribute pdia "
        "    JOIN pathdataiteration pdi ON pdia.pathdata_iteration=pdi.iteration AND pdia.pathdatamaster_id=pdi.pathdatamaster_id "
        "    WHERE pdi.pathdatamaster_id=ANY(:pdm_ids2) UNION "
        "  SELECT instanceattribute_id FROM prdinstiteration_attribute WHERE workspace_id=:ws"
        ")"
    ), {"ws": ws, "pdm_ids2": pdm_ids if pdm_ids else [0]}).fetchall()
    ia_ids = [r[0] for r in ia_rows]

    # queryrule（query 引用的规则树：自引用 parent_query_rule）
    qr_rows = db.execute(text(
        "WITH RECURSIVE rtree AS ("
        "  SELECT qr.qid FROM queryrule qr"
        "  JOIN query q ON q.queryrule_id=qr.qid OR q.pathdata_queryrule_id=qr.qid"
        "  WHERE q.author_workspace_id=:ws"
        "  UNION SELECT child.qid FROM queryrule child JOIN rtree rt ON child.parent_query_rule=rt.qid"
        ") SELECT DISTINCT qid FROM rtree"
    ), {"ws": ws}).fetchall()
    qr_ids = [r[0] for r in qr_rows]

    def _del(sql, **params):
        db.execute(text(sql), params)

    # ── 1. workflow 子系统 ──
    if wf_ids:
        _del("DELETE FROM task_user WHERE activity_step||'/'||workflow_id IN (SELECT step||'/'||CAST(id AS TEXT) FROM activity WHERE workflow_id=ANY(:ids))", ids=wf_ids)
        _del("DELETE FROM task_usergroup WHERE activity_step||'/'||workflow_id IN (SELECT step||'/'||CAST(id AS TEXT) FROM activity WHERE workflow_id=ANY(:ids))", ids=wf_ids)
        _del("DELETE FROM task WHERE activity_step IN (SELECT step FROM activity WHERE workflow_id=ANY(:ids)) AND workflow_id=ANY(:ids)", ids=wf_ids)
        _del("DELETE FROM activity_relaunch WHERE activity_step IN (SELECT step FROM activity WHERE workflow_id=ANY(:ids)) AND activity_workflow_id=ANY(:ids)", ids=wf_ids)
        _del("DELETE FROM activity WHERE workflow_id=ANY(:ids)", ids=wf_ids)
        _del("DELETE FROM workspace_aborted_workflow WHERE workflow_id=ANY(:ids)", ids=wf_ids)
        _del("DELETE FROM part_aborted_workflow WHERE partmaster_workspace_id=:ws", ws=ws)
        _del("DELETE FROM document_aborted_workflow WHERE documentmaster_workspace_id=:ws", ws=ws)
        _del("DELETE FROM workflow WHERE id=ANY(:ids)", ids=wf_ids)
    _del("DELETE FROM workspace_workflow WHERE workspace_id=:ws", ws=ws)

    if wfm_ids:
        _del("DELETE FROM task_user WHERE activity_step||'/'||workflow_id IN (SELECT step||'/'||CAST(workflow_id AS TEXT) FROM activity WHERE workflow_id IN (SELECT id FROM workflow WHERE id IN (SELECT workflow_id FROM workspace_workflow WHERE workspace_id=:ws)))", ws=ws)
        _del("DELETE FROM task_usergroup WHERE activity_step||'/'||workflow_id IN (SELECT step||'/'||CAST(workflow_id AS TEXT) FROM activity WHERE workflow_id IN (SELECT id FROM workflow WHERE id IN (SELECT workflow_id FROM workspace_workflow WHERE workspace_id=:ws)))", ws=ws)
        _del("DELETE FROM task WHERE activity_step IN (SELECT step FROM activity WHERE workflow_id IN (SELECT id FROM workflow WHERE id IN (SELECT workflow_id FROM workspace_workflow WHERE workspace_id=:ws)))", ws=ws)
        _del("DELETE FROM activity_relaunch WHERE activity_step IN (SELECT step FROM activity WHERE workflow_id IN (SELECT id FROM workflow WHERE id IN (SELECT workflow_id FROM workspace_workflow WHERE workspace_id=:ws)))", ws=ws)
        _del("DELETE FROM activity WHERE workflow_id IN (SELECT id FROM workflow WHERE id IN (SELECT workflow_id FROM workspace_workflow WHERE workspace_id=:ws))", ws=ws)
        _del("DELETE FROM taskmodel WHERE activitymodel_id IN (SELECT id FROM activitymodel WHERE workflowmodel_id=ANY(:ids))", ids=wfm_ids)
        _del("DELETE FROM activitymodel_relaunch WHERE activitymodel_id IN (SELECT id FROM activitymodel WHERE workflowmodel_id=ANY(:ids))", ids=wfm_ids)
        _del("DELETE FROM activitymodel WHERE workflowmodel_id=ANY(:ids)", ids=wfm_ids)
        _del("DELETE FROM workflowmodel WHERE workspace_id=:ws", ws=ws)

    # ── 2. PathData 叶子表 → P2P → CI 子表 ──
    if pdm_ids:
        _del("DELETE FROM pathdataiteration_attribute WHERE pathdata_iteration IN (SELECT iteration FROM pathdataiteration WHERE pathdatamaster_id=ANY(:ids)) AND pathdatamaster_id=ANY(:ids)", ids=pdm_ids)
        _del("DELETE FROM pathdataiteration_documentlink WHERE pathdata_iteration IN (SELECT iteration FROM pathdataiteration WHERE pathdatamaster_id=ANY(:ids)) and pathdatamaster_id=ANY(:ids)", ids=pdm_ids)
        _del("DELETE FROM pathdataiteration_binres WHERE pathdatamaster_id=ANY(:ids)", ids=pdm_ids)
        _del("DELETE FROM pathdataiteration WHERE pathdatamaster_id=ANY(:ids)", ids=pdm_ids)
        _del("DELETE FROM prdinstiteration_pathdatamstr WHERE workspace_id=:ws", ws=ws)
        _del("DELETE FROM pathdatamaster WHERE id=ANY(:ids)", ids=pdm_ids)
    if ptl_ids:
        _del("DELETE FROM prdinstiteration_p2plink WHERE pathtopathlink_id=ANY(:ids)", ids=ptl_ids)
        _del("DELETE FROM productbaseline_p2plink WHERE pathtopathlink_id=ANY(:ids)", ids=ptl_ids)
        _del("DELETE FROM configurationitem_p2plink WHERE workspace_id=:ws", ws=ws)
        _del("DELETE FROM pathtopathlink WHERE id=ANY(:ids)", ids=ptl_ids)

    # ── 3. 变更管理 ──
    _del("DELETE FROM changeissue_affected_part WHERE changeissue_id IN (SELECT id FROM changeissue WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM changeissue_affected_document WHERE changeissue_id IN (SELECT id FROM changeissue WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM changeissue_tag WHERE changeissue_id IN (SELECT id FROM changeissue WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM changerequest_changeissue WHERE changerequest_id IN (SELECT id FROM changerequest WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM changerequest_changeissue WHERE changeissue_id IN (SELECT id FROM changeissue WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM changeorder_changerequest WHERE changeorder_id IN (SELECT id FROM changeorder WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM changeorder_changerequest WHERE changerequest_id IN (SELECT id FROM changerequest WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM changeorder_affected_part WHERE changeorder_id IN (SELECT id FROM changeorder WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM changeorder_affected_document WHERE changeorder_id IN (SELECT id FROM changeorder WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM changeorder_tag WHERE changeorder_id IN (SELECT id FROM changeorder WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM changereq_affected_part WHERE changerequest_id IN (SELECT id FROM changerequest WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM changereq_affected_document WHERE changerequest_id IN (SELECT id FROM changerequest WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM changerequest_tag WHERE changerequest_id IN (SELECT id FROM changerequest WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM changeissue WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM changerequest WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM changeorder WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM milestone WHERE workspace_id=:ws", ws=ws)

    # ── 4. 产品实例 / 基线 / 配置项 ──
    _del("DELETE FROM prdinstanceiteration_optlink WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM prdinstanceiteration_sublink WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM prdinstiteration_documentlink WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM prdinstiteration_binres WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM prdinstiteration_attribute WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM productinstanceiteration WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM productinstancemaster WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM productbaseline_optionallink WHERE productbaseline_id IN (SELECT id FROM productbaseline WHERE configurationitem_workspace_id=:ws)", ws=ws)
    _del("DELETE FROM productbaseline_substitutelink WHERE productbaseline_id IN (SELECT id FROM productbaseline WHERE configurationitem_workspace_id=:ws)", ws=ws)
    _del("DELETE FROM prdcfg_optionallink WHERE productbaseline_id IN (SELECT id FROM productbaseline WHERE configurationitem_workspace_id=:ws)", ws=ws)
    _del("DELETE FROM prdcfg_substitutelink WHERE productbaseline_id IN (SELECT id FROM productbaseline WHERE configurationitem_workspace_id=:ws)", ws=ws)
    _del("DELETE FROM productconfiguration WHERE configurationitem_workspace_id=:ws", ws=ws)
    _del("DELETE FROM productbaseline WHERE configurationitem_workspace_id=:ws", ws=ws)
    _del("DELETE FROM effectivity WHERE configurationitem_id IN (SELECT id FROM configurationitem WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM partrevision_effectivity WHERE partmaster_workspace_id=:ws", ws=ws)
    _del("DELETE FROM layer WHERE configurationitem_workspace_id=:ws", ws=ws)
    _del("DELETE FROM configurationitem WHERE workspace_id=:ws", ws=ws)

    # ── 5. 模板（属性模板 + 自身） ──
    # 先捕获模板引用的 instanceattributetemplate id（无 workspace 列，经 join 定位）
    iat_rows = db.execute(text(
        "SELECT instanceattributetemplate_id FROM partmastertemplate_attr WHERE workspace_id=:ws "
        "UNION SELECT instanceattributetemplate_id FROM documentmastertemplate_attr WHERE workspace_id=:ws "
        "UNION SELECT instanceattribute_template_id FROM partiteration_pathdata_attr WHERE workspace_id=:ws"
    ), {"ws": ws}).fetchall()
    iat_ids = [r[0] for r in iat_rows if r[0] is not None]
    _del("DELETE FROM partmastertemplate_attr WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM partmastertemplate WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM documentmastertemplate_attr WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM documentmastertemplate_binres WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM documentmastertemplate WHERE workspace_id=:ws", ws=ws)

    # ── 6. 零件子表（含 instanceattribute） ──
    _del("DELETE FROM partiteration_pathdata_attr WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM partiteration_attribute WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM partiteration_documentlink WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM partiteration_binres WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM partiteration_geometry WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM partiteration_partusagelink WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM partrevision_tag WHERE partmaster_workspace_id=:ws", ws=ws)
    _del("DELETE FROM baselinedpart WHERE target_workspace_id=:ws", ws=ws)
    _del("DELETE FROM conversion WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM modificationnotification WHERE impacted_workspace_id=:ws OR modified_workspace_id=:ws", ws=ws)
    _del("DELETE FROM partsubstitutelink WHERE substitute_workspace_id=:ws", ws=ws)
    _del("DELETE FROM partusagelink WHERE component_workspace_id=:ws", ws=ws)
    _del("DELETE FROM partiteration WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM partrevision WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM partmaster_alternate WHERE partmaster_workspace_id=:ws OR alternate_workspace_id=:ws", ws=ws)
    _del("DELETE FROM partmaster WHERE workspace_id=:ws", ws=ws)

    # ── 7. 文档子表 ──
    _del("DELETE FROM documentiteration_attribute WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM documentiteration_documentlink WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM documentiteration_binres WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM baselineddocument WHERE target_workspace_id=:ws", ws=ws)
    _del("DELETE FROM documentrevision_tag WHERE documentmaster_workspace_id=:ws", ws=ws)
    _del("DELETE FROM documentlink WHERE target_workspace_id=:ws", ws=ws)
    _del("DELETE FROM documentiteration WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM documentrevision WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM documentmaster WHERE workspace_id=:ws", ws=ws)

    # ── 8. 订阅 / shared entity / marker / collection ──
    _del("DELETE FROM iterationchangesubscription WHERE documentmaster_workspace_id=:ws OR subscriber_workspace_id=:ws", ws=ws)
    _del("DELETE FROM statechangesubscription WHERE documentmaster_workspace_id=:ws OR subscriber_workspace_id=:ws", ws=ws)
    _del("DELETE FROM tagusersubscription WHERE subscriber_workspace_id=:ws OR tag_workspace_id=:ws", ws=ws)
    _del("DELETE FROM tagusergroupsubscription WHERE subscriber_workspace_id=:ws OR tag_workspace_id=:ws", ws=ws)
    _del("DELETE FROM sharedentity WHERE entity_workspace_id=:ws OR author_workspace_id=:ws", ws=ws)
    _del("DELETE FROM marker_partmaster WHERE relatedpart_workspace_id=:ws OR relatedpart_partnumber IN (SELECT partmaster_partnumber FROM partrevision WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM marker WHERE author_workspace_id=:ws", ws=ws)
    _del("DELETE FROM partcollection WHERE author_workspace_id=:ws", ws=ws)
    _del("DELETE FROM documentcollection WHERE author_workspace_id=:ws", ws=ws)
    _del("DELETE FROM documentbaseline WHERE author_workspace_id=:ws", ws=ws)

    # ── 9. instanceattribute + instanceattributetemplate（多表引用 → 汇集 id 定位） ──
    if ia_ids:
        _del("DELETE FROM instanceattribute WHERE id=ANY(:ids)", ids=ia_ids)
    # instanceattributetemplate：模板属性模板（无 workspace 列，含 LOV 类型引用 lov）
    if iat_ids:
        _del("DELETE FROM instanceattributetemplate WHERE id=ANY(:ids)", ids=iat_ids)
    _del("DELETE FROM instanceattributetemplate WHERE lov_workspace_id=:ws", ws=ws)

    # ── 10. 标签 ──
    _del("DELETE FROM tag WHERE workspace_id=:ws", ws=ws)

    # ── 11. LOV ──
    _del("DELETE FROM lov_namevalue WHERE lov_workspace_id=:ws", ws=ws)
    _del("DELETE FROM lov WHERE workspace_id=:ws", ws=ws)

    # ── 12. 查询 ──
    if qr_ids:
        _del("DELETE FROM queryrule_values WHERE queryrule_id=ANY(:ids)", ids=qr_ids)
        _del("DELETE FROM queryrule WHERE qid=ANY(:ids)", ids=qr_ids)
    _del("DELETE FROM querycontext WHERE workspaceid=:ws", ws=ws)
    _del("DELETE FROM query_selects WHERE query_id IN (SELECT id FROM query WHERE author_workspace_id=:ws)", ws=ws)
    _del("DELETE FROM query_order_by WHERE query_id IN (SELECT id FROM query WHERE author_workspace_id=:ws)", ws=ws)
    _del("DELETE FROM query_grouped_by WHERE query_id IN (SELECT id FROM query WHERE author_workspace_id=:ws)", ws=ws)
    _del("DELETE FROM query WHERE author_workspace_id=:ws", ws=ws)

    # ── 13. Import 记录 ──
    _del("DELETE FROM import_error WHERE import_id IN (SELECT id FROM import WHERE user_workspace_id=:ws)", ws=ws)
    _del("DELETE FROM import_warning WHERE import_id IN (SELECT id FROM import WHERE user_workspace_id=:ws)", ws=ws)
    _del("DELETE FROM import WHERE user_workspace_id=:ws", ws=ws)

    # ── 14. 角色 ──  
    _del("DELETE FROM role_user WHERE role_workspace_id=:ws OR user_workspace_id=:ws", ws=ws)
    _del("DELETE FROM role_usergroup WHERE role_workspace_id=:ws OR usergroup_workspace_id=:ws", ws=ws)
    _del("DELETE FROM role WHERE workspace_id=:ws", ws=ws)

    # ── 15. 用户 / 组 / 成员关系 ──
    _del("DELETE FROM acluserentry WHERE principal_workspace_id=:ws", ws=ws)
    _del("DELETE FROM aclusergroupentry WHERE principal_workspace_id=:ws", ws=ws)
    _del("DELETE FROM usergroup_user WHERE usergroup_id_workspace_id=:ws OR user_workspace_id=:ws", ws=ws)
    users = db.execute(text("SELECT login FROM userdata WHERE workspace_id=:ws"), {"ws": ws}).fetchall()
    _del("DELETE FROM userdata WHERE workspace_id=:ws", ws=ws)
    for (login,) in users:
        remaining = db.execute(text("SELECT COUNT(*) FROM userdata WHERE login=:l"), {"l": login}).scalar()
        if remaining == 0:
            db.execute(text("DELETE FROM usergroupmapping WHERE login=:l"), {"l": login})
    _del("DELETE FROM workspaceusermembership WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM workspaceusergroupmembership WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM usergroup WHERE workspace_id=:ws", ws=ws)

    # ── 16. 剩余工作区级配置 ──
    _del("DELETE FROM webhook WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM workspacebackoptions WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM workspacefrontoptions WHERE workspace_id=:ws", ws=ws)

    # ── 17. 工作区本身 ──
    db.execute(text("DELETE FROM workspace WHERE id = :id"), {"id": ws})

    db.execute(text("SET LOCAL session_replication_role='origin'"))
    db.commit()
