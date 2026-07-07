"""产品实例集合 JSON 流输出（对标 InstanceCollectionMessageBodyWriter）。

GET /workspaces/{ws}/products/{ci_id}/instance-collection
"""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.file_export.instance_body_writer_tools import generate_instance_stream

router = APIRouter(prefix="/docdoku-plm-server-rest/api")


@router.get("/workspaces/{workspace_id}/products/{ci_id}/instance-collection")
@router.get("/workspaces/{workspace_id}/products/{ci_id}/instance-collection/", include_in_schema=False)
def get_instance_collection(
    workspace_id: str,
    ci_id: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """以流式 JSON 输出产品实例数据。

    对齐 Java InstanceCollectionMessageBodyWriter:
    使用单位矩阵作为全局变换，遍历产品结构树生成 JSON 数组。
    """
    def generate():
        yield from generate_instance_stream(
            output_stream=None,
            workspace_id=workspace_id,
            configuration_item_id=ci_id,
            filter_dict={"type": "latest"},
            db_session=db,
        )

    return StreamingResponse(
        generate(),
        media_type="application/json",
        headers={"Content-Disposition": "inline"},
    )
