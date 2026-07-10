"""文档基线文件批量 ZIP 导出（对标 DocumentBaselineFileExportMessageBodyWriter）。

GET /workspaces/{ws}/document-baselines/{bl_id}/export-zip
"""
import zipfile
import io
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text as sql_text
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services import vault as vault_svc
from app.core.config import settings
from pathlib import Path

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
    # 查询基线文档的二进制文件
    rows = db.execute(sql_text(
        """
        SELECT DISTINCT br.fullname
        FROM baselineddocument bd
        JOIN documentiteration_binres dib ON (
            dib.workspace_id = bd.target_workspace_id
            AND dib.documentmaster_id = bd.target_documentmaster_id
            AND dib.documentrevision_version = bd.target_docrevision_version
            AND dib.iteration = bd.target_iteration
        )
        JOIN binaryresource br ON br.fullname = dib.attachedfile_fullname
        WHERE bd.documentcollection_id = (
            SELECT documentcollection_id FROM documentbaseline
            WHERE id = :bl_id
        )
        """,
    ), {"bl_id": baseline_id}).fetchall()

    if not rows:
        raise HTTPException(404, "基线中没有可导出的文件")

    zip_buffer = io.BytesIO()
    vault_root = Path(settings.VAULT_PATH)

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for (full_name,) in rows:
            file_path = vault_root / full_name
            if not file_path.exists():
                _logger.warning("vault 文件不存在: %s", full_name)
                continue
            data = file_path.read_bytes()
            # ZIP 内路径: attachedFiles/{原始文件名}
            base_name = Path(full_name).name
            arcname = f"attachedFiles/{base_name}"
            zf.writestr(arcname, data)

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="baseline-{baseline_id}.zip"',
            "Content-Length": str(zip_buffer.getbuffer().nbytes),
        },
    )
