"""产品文件批量 ZIP 导出工具（实施 ProductFileExportMessageBodyWriter 的核心逻辑）。

此模块不注册路由，导出函数供 products.py 中的 export-files stub 调用。
"""
import zipfile
import io
import logging
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import text as sql_text
from app.core.config import settings

_logger = logging.getLogger(__name__)


def build_product_export_zip(
    db: Session, workspace_id: str, ci_id: str,
    export_native_cad: bool = True,
    export_document_links: bool = False,
) -> bytes:
    """构建产品文件 ZIP，返回 bytes。

    对齐 Java ProductFileExportMessageBodyWriter.writeTo():
    遍历产品树 nativeCAD + attachedfiles → 按零件编号/文件类型组织 ZIP 目录。
    """
    vault_root = Path(settings.VAULT_PATH)
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        if export_native_cad:
            # 收集产品树中所有零件的 nativeCAD
            native_rows = db.execute(sql_text(
                """
                SELECT DISTINCT pi.partmaster_partnumber, br.full_name
                FROM partiteration pi
                JOIN binaryresource br ON br.full_name = pi.nativecad_file_fullname
                WHERE pi.workspace_id = :ws
                  AND pi.nativecad_file_fullname IS NOT NULL
                """,
            ), {"ws": workspace_id}).fetchall()

            for row in native_rows:
                full_name = row.full_name
                if not full_name:
                    continue
                file_path = vault_root / full_name
                if not file_path.exists():
                    continue
                data = file_path.read_bytes()
                pn = row.partmaster_partnumber
                base = Path(full_name).name
                zf.writestr(f"{pn}/nativecad/{base}", data)

        # 附件
        attach_rows = db.execute(sql_text(
            """
            SELECT DISTINCT pi.partmaster_partnumber, br.full_name
            FROM partiteration pi
            JOIN partiteration_binres pib ON (
                pib.workspace_id = pi.workspace_id
                AND pib.partmaster_partnumber = pi.partmaster_partnumber
                AND pib.partrevision_version = pi.partrevision_version
                AND pib.iteration = pi.iteration
            )
            JOIN binaryresource br ON br.full_name = pib.attachedfile_fullname
            WHERE pi.workspace_id = :ws
            """,
        ), {"ws": workspace_id}).fetchall()

        for row in attach_rows:
            full_name = row.full_name
            if not full_name:
                continue
            file_path = vault_root / full_name
            if not file_path.exists():
                continue
            data = file_path.read_bytes()
            pn = row.partmaster_partnumber
            base = Path(full_name).name
            zf.writestr(f"{pn}/attachedfiles/{base}", data)

    zip_buffer.seek(0)
    return zip_buffer.getvalue()
