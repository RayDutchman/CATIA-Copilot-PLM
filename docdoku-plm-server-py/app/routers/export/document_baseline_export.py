"""文档基线文件批量 ZIP 导出（对标 DocumentBaselineFileExportMessageBodyWriter）。

GET /workspaces/{ws}/document-baselines/{bl_id}/export-zip
"""
import io
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.file_export.document_baseline_file_export import export_document_baseline_to_zip

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
_logger = logging.getLogger(__name__)


@router.get("/workspaces/{workspace_id}/document-baselines/{baseline_id}/export-files")
@router.get("/workspaces/{workspace_id}/document-baselines/{baseline_id}/export-files/", include_in_schema=False)
def export_document_baseline_files(
    workspace_id: str,
    baseline_id: int,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """以 ZIP 格式下载文档基线中的所有文件。

    对齐 Java DocumentBaselineFileExportMessageBodyWriter:
    遍历 baseline → getBinaryResourcesFromBaseline → 将每个文件写入 ZIP。
    """
    zip_bytes = export_document_baseline_to_zip(db, baseline_id)
    if not zip_bytes:
        raise HTTPException(404, "基线中没有可导出的文件")

    zip_buffer = io.BytesIO(zip_bytes)
    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="baseline-{baseline_id}.zip"',
            "Content-Length": str(len(zip_bytes)),
        },
    )
