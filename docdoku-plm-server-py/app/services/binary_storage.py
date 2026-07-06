"""文件服务：vault 写入/读取 + BinaryResource DB 记录。对齐 Payara saveNativeCAD/saveFile。"""
from datetime import datetime
from sqlalchemy.orm import Session
from app.services import vault
from app.models.part import (
    BinaryResource, PartIteration, part_iteration_binres,
)


def _upsert_binaryresource(db: Session, full_name: str, size: int,
                           dtype: str = "BinaryResource") -> BinaryResource:
    br = db.query(BinaryResource).filter(
        BinaryResource.full_name == full_name).first()
    now = datetime.utcnow()
    if br is None:
        br = BinaryResource(full_name=full_name, dtype=dtype,
                            content_length=size, last_modified=now)
        db.add(br)
    else:
        br.content_length = size
        br.last_modified = now
    db.flush()
    return br


def save_nativecad(db: Session, ws: str, pn: str, ver: str, iteration: int,
                   filename: str, data: bytes) -> BinaryResource:
    """写 nativecad 到 vault + upsert BinaryResource + 设 PartIteration.native_cad_file_fullname。"""
    path = vault.part_nativecad_path(ws, pn, ver, iteration, filename)
    vault.write_file(path, data)
    full_name = f"{ws}/parts/{pn}/{ver}/{iteration}/nativecad/{filename}"
    br = _upsert_binaryresource(db, full_name, len(data))
    it = db.query(PartIteration).filter(
        PartIteration.workspace_id == ws,
        PartIteration.partmaster_partnumber == pn,
        PartIteration.partrevision_version == ver,
        PartIteration.iteration == iteration,
    ).first()
    if it is not None:
        it.native_cad_file_fullname = full_name
    db.flush()
    return br


def save_attached(db: Session, ws: str, pn: str, ver: str, iteration: int,
                  filename: str, data: bytes) -> BinaryResource:
    """写附件到 vault + upsert BinaryResource + insert part_iteration_binres 关联。"""
    path = vault.part_attached_path(ws, pn, ver, iteration, filename)
    vault.write_file(path, data)
    full_name = f"{ws}/parts/{pn}/{ver}/{iteration}/attachedfiles/{filename}"
    br = _upsert_binaryresource(db, full_name, len(data))
    exists = db.execute(
        part_iteration_binres.select().where(
            part_iteration_binres.c.workspace_id == ws,
            part_iteration_binres.c.partmaster_partnumber == pn,
            part_iteration_binres.c.partrevision_version == ver,
            part_iteration_binres.c.iteration == iteration,
            part_iteration_binres.c.attachedfile_fullname == full_name,
        )
    ).first()
    if exists is None:
        db.execute(part_iteration_binres.insert().values(
            workspace_id=ws, partmaster_partnumber=pn,
            partrevision_version=ver, iteration=iteration,
            attachedfile_fullname=full_name,
        ))
    db.flush()
    return br


def get_file_bytes(ws: str, pn: str, ver: str, iteration: int,
                   sub_type: str | None, filename: str) -> bytes:
    """从 vault 读文件。sub_type=None 读 {iter}/{filename}（几何体 GLB）。"""
    if sub_type is None:
        from app.services.vault import _vault_root
        path = (_vault_root() / ws / "parts" / pn / ver
                / str(iteration) / filename)
    elif sub_type == "nativecad":
        path = vault.part_nativecad_path(ws, pn, ver, iteration, filename)
    else:
        path = vault.part_attached_path(ws, pn, ver, iteration, filename)
    return vault.read_file(path)

