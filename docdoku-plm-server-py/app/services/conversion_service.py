"""转换回调处理，对齐 Payara handleConversionResultCallback（保留 race/空几何修复）。"""
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from app.core.config import settings
from app.services import vault
from app.models.part import (
    Conversion, BinaryResource, part_iteration_geometry,
)
from app.schemas.part import ConversionResultDTO


def find_pending_conversion(db: Session, ws: str, pn: str,
                            ver: str) -> Conversion | None:
    """查该 revision 下 pending=True 的 Conversion，定位真正发起转换的 iteration。"""
    return db.query(Conversion).filter(
        Conversion.workspace_id == ws,
        Conversion.partmaster_partnumber == pn,
        Conversion.partrevision_version == ver,
        Conversion.pending.is_(True),
    ).first()


def end_conversion(db: Session, conv: Conversion, succeed: bool) -> None:
    conv.pending = False
    conv.succeed = succeed
    conv.end_date = datetime.utcnow()
    db.flush()


def handle_callback(db: Session, ws: str, pn: str, ver: str,
                    result: ConversionResultDTO) -> None:
    conv = find_pending_conversion(db, ws, pn, ver)
    if conv is None:
        return
    iteration = conv.iteration
    err = (result.errorOutput or "")
    if "no geometry generated" in err.lower():
        end_conversion(db, conv, True)
        return
    if err:
        end_conversion(db, conv, False)
        return
    glb_name = (result.convertedFileLODs or {}).get("0")
    if not glb_name:
        end_conversion(db, conv, False)
        return
    src = Path(settings.CONVERSIONS_PATH) / result.tempDir / glb_name
    data = src.read_bytes()
    from app.services.vault import _vault_root
    dst = _vault_root() / ws / "parts" / pn / ver / str(iteration) / glb_name
    vault.write_file(dst, data)
    full_name = f"{ws}/parts/{pn}/{ver}/{iteration}/{glb_name}"
    box = result.box or [0, 0, 0, 0, 0, 0]
    br = db.query(BinaryResource).filter(
        BinaryResource.full_name == full_name).first()
    if br is None:
        br = BinaryResource(
            full_name=full_name, dtype="Geometry",
            content_length=len(data), last_modified=datetime.utcnow(),
            x_min=box[0], y_min=box[1], z_min=box[2],
            x_max=box[3], y_max=box[4], z_max=box[5],
        )
        db.add(br)
        db.flush()
    exists = db.execute(
        part_iteration_geometry.select().where(
            part_iteration_geometry.c.workspace_id == ws,
            part_iteration_geometry.c.partmaster_partnumber == pn,
            part_iteration_geometry.c.partrevision_version == ver,
            part_iteration_geometry.c.iteration == iteration,
            part_iteration_geometry.c.geometry_fullname == full_name,
        )
    ).first()
    if exists is None:
        db.execute(part_iteration_geometry.insert().values(
            workspace_id=ws, partmaster_partnumber=pn,
            partrevision_version=ver, iteration=iteration,
            geometry_fullname=full_name,
        ))
    end_conversion(db, conv, True)
