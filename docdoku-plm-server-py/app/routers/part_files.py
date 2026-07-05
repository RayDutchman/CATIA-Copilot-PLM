"""零件文件上传/下载端点，路径 /api/files/{ws}/parts/...（对齐 Payara PartBinaryResource）。"""
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Request, HTTPException, Body
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import NotAllowedException
from app.models.auth import Account
from app.services import binary_storage
from app.services.product_manager import ProductService
from app.services.kafka_producer import send_conversion_order
from app.services.converter import find_pending_conversion
from app.models.part import PartIteration
from datetime import datetime, timedelta, timezone

router = APIRouter()
svc = ProductService()

CAD_WHITELIST = {"stp", "step", "igs", "iges", "stl", "off", "ply", "obj", "dae", "ifc"}


def _check_writable(db: Session, ws: str, pn: str, ver: str,
                    iteration: int, user_login: str) -> None:
    """签出用户 && 最新迭代，否则 NotAllowedException4。"""
    pr = svc.get_revision(db, ws, pn, ver)
    if pr.checkout_user_login != user_login or pr.last_iteration_number != iteration:
        raise NotAllowedException("NotAllowedException4")


@router.post("/files/{ws}/parts/{pn}/{ver}/{iteration}/nativecad", status_code=201)
@router.post("/files/{ws}/parts/{pn}/{ver}/{iteration}/nativecad/",
             status_code=201, include_in_schema=False)
def upload_nativecad(
    ws: str, pn: str, ver: str, iteration: int,
    request: Request,
    upload: UploadFile = File(...),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_writable(db, ws, pn, ver, iteration, current_user.login)
    ext = Path(upload.filename).suffix.lstrip(".").lower()
    if ext not in CAD_WHITELIST:
        raise HTTPException(400, "Unsupported CAD file format")
    data = upload.file.read()
    binary_storage.save_nativecad(db, ws, pn, ver, iteration, upload.filename, data)
    # Fix 2: 检查是否已有 pending Conversion，避免重复发送 Kafka
    existing = find_pending_conversion(db, ws, pn, ver)
    if existing:
        db.commit()
        return {"status": "uploaded", "message": "Conversion already pending, skipped"}
    svc.create_conversion(db, ws, pn, ver, iteration)
    db.commit()
    auth = request.headers.get("authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    send_conversion_order(ws, pn, ver, iteration, upload.filename, token)
    return {"status": "uploaded"}


@router.post("/files/{ws}/parts/{pn}/{ver}/{iteration}/attachedfiles", status_code=201)
@router.post("/files/{ws}/parts/{pn}/{ver}/{iteration}/attachedfiles/",
             status_code=201, include_in_schema=False)
def upload_attached(
    ws: str, pn: str, ver: str, iteration: int,
    upload: UploadFile = File(...),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_writable(db, ws, pn, ver, iteration, current_user.login)
    data = upload.file.read()
    binary_storage.save_attached(db, ws, pn, ver, iteration, upload.filename, data)
    db.commit()
    return {"status": "uploaded"}


@router.delete("/files/{ws}/parts/{pn}/{ver}/{iteration}/{sub_type}/{file_name}",
               status_code=204)
@router.delete("/files/{ws}/parts/{pn}/{ver}/{iteration}/{sub_type}/{file_name}/",
               status_code=204, include_in_schema=False)
def delete_part_file(
    ws: str, pn: str, ver: str, iteration: int, sub_type: str, file_name: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_writable(db, ws, pn, ver, iteration, current_user.login)
    full_name = f"{ws}/parts/{pn}/{ver}/{iteration}/{sub_type}/{file_name}"
    from app.models.part import BinaryResource, part_iteration_binres, part_iteration_geometry
    from app.services import vault
    from app.core.config import settings
    from pathlib import Path

    # 根据 sub_type 清理关联表
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

    # 删除 vault 物理文件
    try:
        vault_path = Path(settings.VAULT_PATH) / full_name
        if vault_path.exists():
            vault_path.unlink()
    except Exception:
        pass

    db.commit()


@router.put("/files/{ws}/parts/{pn}/{ver}/{iteration}/{sub_type}/{file_name}",
            status_code=200)
@router.put("/files/{ws}/parts/{pn}/{ver}/{iteration}/{sub_type}/{file_name}/",
            status_code=200, include_in_schema=False)
def rename_part_file(
    ws: str, pn: str, ver: str, iteration: int, sub_type: str, file_name: str,
    body: dict = Body(...),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_writable(db, ws, pn, ver, iteration, current_user.login)
    new_file_name = body.get("fileName")
    if not new_file_name:
        raise HTTPException(400, "fileName is required")
    old_full = f"{ws}/parts/{pn}/{ver}/{iteration}/{sub_type}/{file_name}"
    new_full = f"{ws}/parts/{pn}/{ver}/{iteration}/{sub_type}/{new_file_name}"

    from app.models.part import BinaryResource, part_iteration_binres, part_iteration_geometry
    from app.services import vault
    from app.core.config import settings
    from pathlib import Path

    # 更新 BinaryResource
    br = db.query(BinaryResource).filter(
        BinaryResource.full_name == old_full).first()
    if br:
        br.full_name = new_full

    # 更新关联表
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

    # 重命名 vault 物理文件
    try:
        old_path = Path(settings.VAULT_PATH) / old_full
        new_path = Path(settings.VAULT_PATH) / new_full
        if old_path.exists():
            new_path.parent.mkdir(parents=True, exist_ok=True)
            old_path.rename(new_path)
    except Exception:
        pass

    db.commit()
    return {"status": "renamed", "fileName": new_file_name}
@router.get("/files/{ws}/parts/{pn}/{ver}/{iteration}/{sub_type}/{file_name}")
@router.get("/files/{ws}/parts/{pn}/{ver}/{iteration}/{sub_type}/{file_name}/", include_in_schema=False)
def download_with_subtype(
    ws: str, pn: str, ver: str, iteration: int, sub_type: str, file_name: str,
    current_user: Account = Depends(get_current_user),
):
    try:
        data = binary_storage.get_file_bytes(ws, pn, ver, iteration, sub_type, file_name)
    except FileNotFoundError:
        raise HTTPException(404, "File not found")
    return Response(content=data, media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{file_name}"',
            "Cache-Control": "max-age=86400",
            "Last-Modified": datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT"),
            "ETag": f'"{file_name}_{len(data)}"',
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, HEAD",
        })


@router.get("/files/{ws}/parts/{pn}/{ver}/{iteration}/{file_name}")
@router.get("/files/{ws}/parts/{pn}/{ver}/{iteration}/{file_name}/", include_in_schema=False)
def download_direct(
    ws: str, pn: str, ver: str, iteration: int, file_name: str,
    current_user: Account = Depends(get_current_user),
):
    """几何体 GLB 直下（fullname 无 subType 段）。"""
    try:
        data = binary_storage.get_file_bytes(ws, pn, ver, iteration, None, file_name)
    except FileNotFoundError:
        raise HTTPException(404, "File not found")
    return Response(content=data, media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{file_name}"',
            "Cache-Control": "max-age=86400",
            "Last-Modified": datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT"),
            "ETag": f'"{file_name}_{len(data)}"',
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, HEAD",
        })

