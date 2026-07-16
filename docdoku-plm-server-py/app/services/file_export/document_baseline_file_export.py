"""文档基线导出上下文（对标 DocumentBaselineFileExport DTO）。"""
from dataclasses import dataclass
import io
import zipfile
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.services import vault
import logging

_logger = logging.getLogger(__name__)


@dataclass
class DocumentBaselineFileExport:
    workspace_id: str
    baseline_id: int


def export_document_baseline_to_zip(db: Session, baseline_id: int) -> bytes:
    """生成文档基线文件 ZIP。"""
    rows = db.execute(text(
        """
        SELECT br.fullname
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
        """
    ), {"bl_id": baseline_id}).fetchall()

    if not rows:
        return None

    zip_buffer = io.BytesIO()
    vault_root = vault.export_zip_base()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for (full_name,) in rows:
            file_path = vault_root / full_name
            if not file_path.exists():
                _logger.warning("vault 文件不存在: %s", full_name)
                continue
            data = vault.read_file(file_path)
            # ZIP 内路径: attachedFiles/{原始文件名}
            base_name = Path(full_name).name
            arcname = f"attachedFiles/{base_name}"
            zf.writestr(arcname, data)

    return zip_buffer.getvalue()
