"""工作区 CRUD 端点。"""
from pathlib import Path
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import (
    NotAllowedException,
    TagAlreadyExistsException, TagNotFoundException,
    ListOfValuesNotFoundException,
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
from app.services.lov_manager import lov_service
from app.services.user_manager import user_mgmt_service
from app.services.workspace_deletion import cascade_delete_workspace

router = APIRouter(prefix="/docdoku-plm-server-rest/api")


def _check_workspace_admin(db: Session, ws: str, current_user: Account):
    """验证当前用户是全局管理员或工作区管理员，否则 403。"""
    workspace_service.check_workspace_admin(db, ws, current_user.login)


def _row_to_dict(r) -> dict:
    return {
        "id": r[0],
        "description": r[1] or "",
        "enabled": bool(r[2]) if r[2] is not None else True,
        "folderLocked": bool(r[3]) if r[3] is not None else False,
    }


@router.get("/workspaces", response_model=WorkspaceListDTO)
@router.get("/workspaces/", include_in_schema=False)
def list_workspaces(db: Session = Depends(get_db),
                    current_user: Account = Depends(get_current_user)):
    return workspace_service.list_workspaces_for_user(db, current_user.login)


@router.get("/workspaces/more", response_model=List[WorkspaceDTO])
@router.get("/workspaces/more/", include_in_schema=False)
def list_more_workspaces(db: Session = Depends(get_db),
                         current_user: Account = Depends(get_current_user)):
    """GetDTO: 返回用户可切换的更多 Workspace 列表。"""
    return workspace_service.list_more_workspaces_for_user(db, current_user.login)


@router.get("/workspaces/reachable-users", response_model=List[UserDTO])
@router.get("/workspaces/reachable-users/", include_in_schema=False)
def reachable_users(db: Session = Depends(get_db),
                    current_user: Account = Depends(get_current_user)):
    """返回与当前用户有共同工作区的其他用户。对齐 Java WorkspaceResource.getReachableUsersForCaller → UserDTO[]"""
    return workspace_service.get_reachable_users(db, current_user.login)


@router.get("/workspaces/{ws}/stats-overview", response_model=StatsOverviewDTO)
@router.get("/workspaces/{ws}/stats-overview/", include_in_schema=False)
def stats_overview(ws: str, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    return workspace_service.get_stats_overview(db, ws)





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
    return workspace_service.get_checked_out_stats(db, ws, "documentrevision")


@router.get("/workspaces/{ws}/checked-out-parts-stats", response_model=Dict[str, List[dict]])
@router.get("/workspaces/{ws}/checked-out-parts-stats/", include_in_schema=False)
def checked_out_parts_stats(ws: str, db: Session = Depends(get_db),
                            current_user: Account = Depends(get_current_user)):
    return workspace_service.get_checked_out_stats(db, ws, "partrevision")


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
    return lov_service.get_lovs_with_values(db, ws)


@router.post("/workspaces/{ws}/lov", status_code=201, response_model=LOVDTO)
@router.post("/workspaces/{ws}/lov/", status_code=201, include_in_schema=False)
def create_lov(ws: str, body: dict, db: Session = Depends(get_db),
               current_user: Account = Depends(get_current_user)):
    name = body.get("name", "").strip()
    if not name:
        raise NotAllowedException("NotAllowedException9", name)
    values = body.get("values", [])
    name_value_pairs = [{"name": v.get("name", ""), "value": v.get("value", ""), "order": i}
                        for i, v in enumerate(values)]
    lov_service.create_lov(db, ws, name, name_value_pairs)
    return {"name": name, "workspaceId": ws, "values": values}


@router.put("/workspaces/{ws}/lov/{name}", response_model=LOVDTO)
@router.put("/workspaces/{ws}/lov/{name}/", include_in_schema=False)
def update_lov(ws: str, name: str, body: dict, db: Session = Depends(get_db),
               current_user: Account = Depends(get_current_user)):
    if not lov_service.lov_exists(db, ws, name):
        raise ListOfValuesNotFoundException("ListOfValuesNotFoundException", name)
    values = body.get("values", [])
    name_value_pairs = [{"name": v.get("name", ""), "value": v.get("value", ""), "order": i}
                        for i, v in enumerate(values)]
    lov_service.update_lov(db, ws, name, name, name_value_pairs)
    return {"name": name, "workspaceId": ws, "values": values}


@router.delete("/workspaces/{ws}/lov/{name}", status_code=204)
@router.delete("/workspaces/{ws}/lov/{name}/", status_code=204, include_in_schema=False)
def delete_lov(ws: str, name: str, db: Session = Depends(get_db),
               current_user: Account = Depends(get_current_user)):
    if not lov_service.lov_exists(db, ws, name):
        raise ListOfValuesNotFoundException("ListOfValuesNotFoundException", name)
    lov_service.delete_lov(db, ws, name)


@router.get("/workspaces/{ws}/attributes/part-iterations", response_model=List[str])
@router.get("/workspaces/{ws}/attributes/part-iterations/", include_in_schema=False)
def attributes_part_iterations(ws: str, db: Session = Depends(get_db),
                               current_user: Account = Depends(get_current_user)):
    return workspace_service.get_workspace_attributes_part_iterations(db, ws)


@router.get("/workspaces/{ws}/attributes/path-data", response_model=List[str])
@router.get("/workspaces/{ws}/attributes/path-data/", include_in_schema=False)
def attributes_path_data(ws: str, db: Session = Depends(get_db),
                         current_user: Account = Depends(get_current_user)):
    return workspace_service.get_workspace_attributes_path_data(db, ws)


@router.get("/workspaces/{ws}", response_model=WorkspaceDTO)
@router.get("/workspaces/{ws}/", include_in_schema=False)
def get_workspace(ws: str, db: Session = Depends(get_db),
                  current_user: Account = Depends(get_current_user)):
    r = workspace_service.get_workspace_admin(db, ws)
    return _row_to_dict(r)


@router.post("/workspaces", status_code=201, response_model=WorkspaceDTO)
@router.post("/workspaces/", status_code=201, include_in_schema=False)
def create_workspace(body: dict, db: Session = Depends(get_db),
                     current_user: Account = Depends(get_current_user),
                     userLogin: str = Query(None)):
    # 业务逻辑归属 workspace_manager（tracker S-029 WorkspaceManagerBean → workspace_manager.py）
    ws_id = body.get("id", "").strip()
    admin = userLogin or current_user.login
    return workspace_service.create_workspace(
        db, ws_id, admin_login=admin, current_user_login=current_user.login,
        description=body.get("description", ""),
        folder_locked=body.get("folderLocked", False),
    )


@router.put("/workspaces/{ws}", response_model=WorkspaceDTO)
@router.put("/workspaces/{ws}/", include_in_schema=False)
def update_workspace(ws: str, body: dict, db: Session = Depends(get_db),
                     current_user: Account = Depends(get_current_user)):
    description = body.get("description")
    folder_locked = body.get("folderLocked")
    r = workspace_service.update_workspace(db, ws, description=description,
                                             folder_locked=folder_locked)
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
    if not user_mgmt_service.is_workspace_member(db, ws, new_admin):
        raise NotAllowedException("NotAllowedException9", new_admin)
    r = workspace_service.change_admin(db, ws, new_admin)
    return _row_to_dict(r)


@router.delete("/workspaces/{ws}", status_code=202)
def delete_workspace(ws: str, db: Session = Depends(get_db),
                     current_user: Account = Depends(get_current_user)):
    _check_workspace_admin(db, ws, current_user)
    workspace_service.get_workspace_admin(db, ws)  # 存在性校验，不存在会抛异常
    cascade_delete_workspace(db, ws)
