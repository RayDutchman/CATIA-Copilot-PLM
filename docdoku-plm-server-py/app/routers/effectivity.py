"""效应端点（EffectivityResource + PartEffectivityResource）。"""
from fastapi import APIRouter, Depends, Body
from fastapi.responses import Response
from app.core.deps import get_current_user
from app.models.auth import Account

router = APIRouter(prefix="/docdoku-plm-server-rest/api")


@router.get("/workspaces/{workspace_id}/parts/{part_key}/effectivities")
@router.get("/workspaces/{workspace_id}/parts/{part_key}/effectivities/", include_in_schema=False)
def get_effectivities(workspace_id: str, part_key: str,
                      current_user: Account = Depends(get_current_user)):
    return []


@router.post("/workspaces/{workspace_id}/parts/{part_key}/effectivities", status_code=201)
@router.post("/workspaces/{workspace_id}/parts/{part_key}/effectivities/", status_code=201, include_in_schema=False)
def create_effectivity(workspace_id: str, part_key: str, body: dict = Body(...),
                       current_user: Account = Depends(get_current_user)):
    return Response(status_code=201)


@router.delete("/workspaces/{workspace_id}/parts/{part_key}/effectivities/{effectivity_id}", status_code=204)
@router.delete("/workspaces/{workspace_id}/parts/{part_key}/effectivities/{effectivity_id}/", status_code=204, include_in_schema=False)
def delete_effectivity(workspace_id: str, part_key: str, effectivity_id: int,
                       current_user: Account = Depends(get_current_user)):
    return Response(status_code=204)
