"""LOV（List of Values）端点（LOVResource）。

GET/POST   /workspaces/{ws}/lov
GET/PUT/DELETE /workspaces/{ws}/lov/{name}
"""
from fastapi import APIRouter, Depends, Body
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import AccessRightException
from app.models.auth import Account
from app.services.lov_manager import lov_service
from app.services.factory.acl_factory import check_write_access

router = APIRouter(prefix="/docdoku-plm-server-rest/api")


@router.get("/workspaces/{workspace_id}/lov")
@router.get("/workspaces/{workspace_id}/lov/", include_in_schema=False)
def get_lovs(
    workspace_id: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取工作空间所有 LOV 列表。"""
    rows = lov_service.find_lov_from_workspace(db, workspace_id)
    result = []
    for row in rows:
        dto = lov_service.build_lov_dto(db, workspace_id, row)
        dto["deletable"] = lov_service.is_lov_deletable(db, workspace_id, row["name"])
        result.append(dto)
    return result


@router.post("/workspaces/{workspace_id}/lov", status_code=201)
@router.post("/workspaces/{workspace_id}/lov/", status_code=201, include_in_schema=False)
def create_lov(
    workspace_id: str,
    body: dict = Body(...),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建 LOV（含选项值列表）。"""
    check_write_access(db, None, current_user.login, False, workspace_id=workspace_id)
    name = body.get("name", "")
    values = body.get("values", [])
    lov_service.create_lov(db, workspace_id, name, values)
    row = lov_service.find_lov(db, workspace_id, name)
    return lov_service.build_lov_dto(db, workspace_id, row)


@router.get("/workspaces/{workspace_id}/lov/{lov_name}")
@router.get("/workspaces/{workspace_id}/lov/{lov_name}/", include_in_schema=False)
def get_lov(
    workspace_id: str,
    lov_name: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取指定 LOV。"""
    row = lov_service.find_lov(db, workspace_id, lov_name)
    return lov_service.build_lov_dto(db, workspace_id, row)


@router.put("/workspaces/{workspace_id}/lov/{lov_name}")
@router.put("/workspaces/{workspace_id}/lov/{lov_name}/", include_in_schema=False)
def update_lov(
    workspace_id: str,
    lov_name: str,
    body: dict = Body(...),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新 LOV 名称与选项值列表。"""
    check_write_access(db, None, current_user.login, False, workspace_id=workspace_id)
    new_name = body.get("name", lov_name)
    values = body.get("values", [])
    lov_service.update_lov(db, workspace_id, lov_name, new_name, values)
    row = lov_service.find_lov(db, workspace_id, new_name)
    return lov_service.build_lov_dto(db, workspace_id, row)


@router.delete("/workspaces/{workspace_id}/lov/{lov_name}", status_code=204)
@router.delete("/workspaces/{workspace_id}/lov/{lov_name}/", status_code=204, include_in_schema=False)
def delete_lov(
    workspace_id: str,
    lov_name: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除 LOV。"""
    check_write_access(db, None, current_user.login, False, workspace_id=workspace_id)
    lov_service.delete_lov(db, workspace_id, lov_name)
    return Response(status_code=204)
