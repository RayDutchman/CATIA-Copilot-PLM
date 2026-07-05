"""共享文档/零件端点（公开访问，无需认证）。"""
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/docdoku-plm-server-rest/api")


@router.get("/shared/{uuid}/documents")
@router.get("/shared/{uuid}/documents/", include_in_schema=False)
def get_shared_documents(uuid: str):
    raise HTTPException(status_code=404, detail="共享文档不存在")


@router.get("/shared/{uuid}/parts")
@router.get("/shared/{uuid}/parts/", include_in_schema=False)
def get_shared_parts(uuid: str):
    raise HTTPException(status_code=404, detail="共享零件不存在")

