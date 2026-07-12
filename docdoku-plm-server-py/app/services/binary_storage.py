"""文件服务：vault 写入/读取 + BinaryResource DB 记录。对齐 Payara saveNativeCAD/saveFile。"""
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from app.services import vault
from app.core.exceptions import FileAlreadyExistsException, FileNotFoundException
from app.models.part import (
    BinaryResource, PartIteration, part_iteration_binres,
)


def _vault_root() -> Path:
    from app.core.config import settings
    return Path(settings.VAULT_PATH)


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


def _delete_old_geometries(db: Session, ws: str, pn: str, ver: str, iteration: int) -> None:
    """删除该 iteration 的所有旧几何体记录（对齐 Java saveNativeCADInPartIteration
    先删 geometry 再删 nativecad 再建新的）。"""
    from app.models.part import part_iteration_geometry
    old_geo_rows = db.execute(
        part_iteration_geometry.select().where(
            part_iteration_geometry.c.workspace_id == ws,
            part_iteration_geometry.c.partmaster_partnumber == pn,
            part_iteration_geometry.c.partrevision_version == ver,
            part_iteration_geometry.c.iteration == iteration,
        )
    ).fetchall()
    for row in old_geo_rows:
        db.query(BinaryResource).filter(
            BinaryResource.full_name == row.geometry_fullname,
        ).delete(synchronize_session=False)
    db.execute(
        part_iteration_geometry.delete().where(
            part_iteration_geometry.c.workspace_id == ws,
            part_iteration_geometry.c.partmaster_partnumber == pn,
            part_iteration_geometry.c.partrevision_version == ver,
            part_iteration_geometry.c.iteration == iteration,
        )
    )


def save_nativecad(db: Session, ws: str, pn: str, ver: str, iteration: int,
                   filename: str, data: bytes) -> BinaryResource:
    """写 nativecad 到 vault + upsert BinaryResource + 设 PartIteration.native_cad_file_fullname。
    对齐 Java saveNativeCADInPartIteration：先删除旧几何体再保存新 CAD。"""
    _delete_old_geometries(db, ws, pn, ver, iteration)
    full_name = f"{ws}/parts/{pn}/{ver}/{iteration}/nativecad/{filename}"
    existing = db.query(BinaryResource).filter(
        BinaryResource.full_name == full_name).first()
    if existing is not None:
        raise FileAlreadyExistsException("FileAlreadyExistsException", full_name)
    path = vault.part_nativecad_path(ws, pn, ver, iteration, filename)
    vault.write_file(path, data)
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
    full_name = f"{ws}/parts/{pn}/{ver}/{iteration}/attachedfiles/{filename}"
    existing = db.query(BinaryResource).filter(
        BinaryResource.full_name == full_name).first()
    if existing is not None:
        raise FileAlreadyExistsException("FileAlreadyExistsException", full_name)
    path = vault.part_attached_path(ws, pn, ver, iteration, filename)
    vault.write_file(path, data)
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
    """从 vault 读文件，若当前 iteration 不存在则回退到更早 iteration。"""
    if sub_type is None:
        full_name = f"{ws}/parts/{pn}/{ver}/{iteration}/{filename}"
    elif sub_type == "nativecad":
        full_name = f"{ws}/parts/{pn}/{ver}/{iteration}/nativecad/{filename}"
    else:
        full_name = f"{ws}/parts/{pn}/{ver}/{iteration}/attachedfiles/{filename}"
    for iter_num in range(iteration, 0, -1):
        try:
            if sub_type is None:
                path = (_vault_root() / ws / "parts" / pn / ver
                        / str(iter_num) / filename)
            elif sub_type == "nativecad":
                path = vault.part_nativecad_path(ws, pn, ver, iter_num, filename)
            else:
                path = vault.part_attached_path(ws, pn, ver, iter_num, filename)
            return vault.read_file(path)
        except FileNotFoundError:
            if iter_num == 1:
                raise FileNotFoundException("FileNotFoundException", full_name)
            continue
    raise FileNotFoundException("FileNotFoundException", full_name)


def delete_part_file(db: Session, ws: str, pn: str, ver: str, iteration: int,
                     sub_type: str, file_name: str,
                     user_login: str) -> None:
    """删除零件文件（含关联表清理 + vault 物理删除）。"""
    from app.core.exceptions import NotAllowedException
    from app.core.config import settings
    from app.models.part import BinaryResource, part_iteration_binres, part_iteration_geometry

    full_name = f"{ws}/parts/{pn}/{ver}/{iteration}/{sub_type}/{file_name}"

    if sub_type == "nativecad":
        it = db.query(PartIteration).filter(
            PartIteration.workspace_id == ws,
            PartIteration.partmaster_partnumber == pn,
            PartIteration.partrevision_version == ver,
            PartIteration.iteration == iteration,
        ).first()
        if it:
            it.native_cad_file_fullname = None
    elif sub_type == "attachedfiles":
        db.execute(part_iteration_binres.delete().where(
            part_iteration_binres.c.workspace_id == ws,
            part_iteration_binres.c.partmaster_partnumber == pn,
            part_iteration_binres.c.partrevision_version == ver,
            part_iteration_binres.c.iteration == iteration,
            part_iteration_binres.c.attachedfile_fullname == full_name,
        ))
    else:
        db.execute(part_iteration_geometry.delete().where(
            part_iteration_geometry.c.workspace_id == ws,
            part_iteration_geometry.c.partmaster_partnumber == pn,
            part_iteration_geometry.c.partrevision_version == ver,
            part_iteration_geometry.c.iteration == iteration,
            part_iteration_geometry.c.geometry_fullname == full_name,
        ))

    try:
        vault_path = Path(settings.VAULT_PATH) / full_name
        if vault_path.exists():
            vault_path.unlink()
    except Exception:
        pass

    db.commit()


def rename_part_file(db: Session, ws: str, pn: str, ver: str, iteration: int,
                     sub_type: str, old_name: str, new_name: str,
                     user_login: str) -> dict:
    """重命名零件文件（含关联表 + vault 物理重命名）。"""
    from fastapi import HTTPException
    from app.core.config import settings
    from app.models.part import BinaryResource, part_iteration_binres, part_iteration_geometry

    old_full = f"{ws}/parts/{pn}/{ver}/{iteration}/{sub_type}/{old_name}"
    new_full = f"{ws}/parts/{pn}/{ver}/{iteration}/{sub_type}/{new_name}"

    br = db.query(BinaryResource).filter(
        BinaryResource.full_name == old_full).first()
    if br:
        br.full_name = new_full

    if sub_type == "nativecad":
        it = db.query(PartIteration).filter(
            PartIteration.workspace_id == ws,
            PartIteration.partmaster_partnumber == pn,
            PartIteration.partrevision_version == ver,
            PartIteration.iteration == iteration,
        ).first()
        if it:
            it.native_cad_file_fullname = new_full
    elif sub_type == "attachedfiles":
        db.execute(part_iteration_binres.update().where(
            part_iteration_binres.c.workspace_id == ws,
            part_iteration_binres.c.partmaster_partnumber == pn,
            part_iteration_binres.c.partrevision_version == ver,
            part_iteration_binres.c.iteration == iteration,
            part_iteration_binres.c.attachedfile_fullname == old_full,
        ).values(attachedfile_fullname=new_full))
    else:
        db.execute(part_iteration_geometry.update().where(
            part_iteration_geometry.c.workspace_id == ws,
            part_iteration_geometry.c.partmaster_partnumber == pn,
            part_iteration_geometry.c.partrevision_version == ver,
            part_iteration_geometry.c.iteration == iteration,
            part_iteration_geometry.c.geometry_fullname == old_full,
        ).values(geometry_fullname=new_full))

    try:
        old_path = Path(settings.VAULT_PATH) / old_full
        new_path = Path(settings.VAULT_PATH) / new_full
        if old_path.exists():
            new_path.parent.mkdir(parents=True, exist_ok=True)
            old_path.rename(new_path)
    except Exception:
        pass

    db.commit()
    return {"fullName": new_full, "name": new_name}

