"""LOV（List of Values）端点（LOVResource）。

GET/POST   /workspaces/{ws}/lov
GET/PUT/DELETE /workspaces/{ws}/lov/{name}
"""
from fastapi import APIRouter, Depends, Body
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.lov_manager import lov_service

router = APIRouter(prefix="/docdoku-plm-server-rest/api")


def _build_lov_dto(lov_row: dict, db, ws: str) -> dict:
    """将 lov 行 + 关联 namevalues 组装成 DTO。"""
    from sqlalchemy import text
    attrs = db.execute(text(
        "SELECT name, value FROM lov_namevalue "
        "WHERE lov_workspace_id = :ws AND lov_name = :n ORDER BY namevalue_order"
    ), {"ws": ws, "n": lov_row["name"]}).fetchall()
    return {
        "name": lov_row["name"],
        "workspaceId": lov_row["workspace_id"],
        "values": [{"name": r[0], "value": r[1]} for r in attrs],
    }


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
        dto = _build_lov_dto(row, db, workspace_id)
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
    name = body.get("name", "")
    values = body.get("values", [])
    lov_service.create_lov(db, workspace_id, name, values)
    row = lov_service.find_lov(db, workspace_id, name)
    return _build_lov_dto(row, db, workspace_id)


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
    return _build_lov_dto(row, db, workspace_id)


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
    new_name = body.get("name", lov_name)
    values = body.get("values", [])
    lov_service.update_lov(db, workspace_id, lov_name, new_name, values)
    row = lov_service.find_lov(db, workspace_id, new_name)
    return _build_lov_dto(row, db, workspace_id)


@router.delete("/workspaces/{workspace_id}/lov/{lov_name}", status_code=204)
@router.delete("/workspaces/{workspace_id}/lov/{lov_name}/", status_code=204, include_in_schema=False)
def delete_lov(
    workspace_id: str,
    lov_name: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除 LOV。"""
    lov_service.delete_lov(db, workspace_id, lov_name)
    return Response(status_code=204)
