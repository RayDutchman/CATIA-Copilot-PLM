"""产品导出上下文（对标 ProductFileExport DTO）。"""
from dataclasses import dataclass, field
import zipfile
import io
import logging
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import text as sql_text
from app.services import vault

_logger = logging.getLogger(__name__)


@dataclass
class ProductFileExport:
    workspace_id: str
    configuration_item_id: str
    ps_filter: dict | None = None  # ProductStructureFilter 描述
    serial_number: str | None = None
    baseline_id: int | None = None
    export_native_cad: bool = False
    export_document_links: bool = False
    binaries_in_tree: dict[str, set[str]] = field(default_factory=dict)


def build_product_export_zip(
    db: Session, workspace_id: str, ci_id: str,
    export_native_cad: bool = True,
    export_document_links: bool = False,
) -> bytes:
    """构建产品文件 ZIP，返回 bytes。"""
    vault_root = vault.export_zip_base()
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        if export_native_cad:
            native_rows = db.execute(sql_text(
                """
                SELECT DISTINCT pi.partmaster_partnumber, br.fullname
                FROM partiteration pi
                JOIN binaryresource br ON br.fullname = pi.nativecadfile_fullname
                WHERE pi.workspace_id = :ws
                  AND pi.nativecadfile_fullname IS NOT NULL
                """,
            ), {"ws": workspace_id}).fetchall()

            for row in native_rows:
                full_name = row.fullname
                if not full_name:
                    continue
                file_path = vault_root / full_name
                if not file_path.exists():
                    continue
                data = vault.read_file(file_path)
                pn = row.partmaster_partnumber
                base = Path(full_name).name
                zf.writestr(f"{pn}/nativecad/{base}", data)

        attach_rows = db.execute(sql_text(
            """
            SELECT DISTINCT pi.partmaster_partnumber, br.fullname
            FROM partiteration pi
            JOIN partiteration_binres pib ON (
                pib.workspace_id = pi.workspace_id
                AND pib.partmaster_partnumber = pi.partmaster_partnumber
                AND pib.partrevision_version = pi.partrevision_version
                AND pib.iteration = pi.iteration
            )
            JOIN binaryresource br ON br.fullname = pib.attachedfile_fullname
            WHERE pi.workspace_id = :ws
            """,
        ), {"ws": workspace_id}).fetchall()

        for row in attach_rows:
            full_name = row.fullname
            if not full_name:
                continue
            file_path = vault_root / full_name
            if not file_path.exists():
                continue
            data = vault.read_file(file_path)
            pn = row.partmaster_partnumber
            base = Path(full_name).name
            zf.writestr(f"{pn}/attachedfiles/{base}", data)

    return zip_buffer.getvalue()
