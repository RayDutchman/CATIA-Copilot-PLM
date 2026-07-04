"""零件文件上传/下载端点，路径 /api/files/{ws}/parts/...（对齐 Payara PartBinaryResource）。"""
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Request, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import NotAllowedException
from app.models.auth import Account
from app.services import file_service
from app.services.product_service import ProductService
from app.services.kafka_producer import send_conversion_order

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
    file_service.save_nativecad(db, ws, pn, ver, iteration, upload.filename, data)
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
    file_service.save_attached(db, ws, pn, ver, iteration, upload.filename, data)
    db.commit()
    return {"status": "uploaded"}


@router.get("/files/{ws}/parts/{pn}/{ver}/{iteration}/{sub_type}/{file_name}")
def download_with_subtype(
    ws: str, pn: str, ver: str, iteration: int, sub_type: str, file_name: str,
    current_user: Account = Depends(get_current_user),
):
    try:
        data = file_service.get_file_bytes(ws, pn, ver, iteration, sub_type, file_name)
    except FileNotFoundError:
        raise HTTPException(404, "File not found")
    return Response(content=data, media_type="application/octet-stream")


@router.get("/files/{ws}/parts/{pn}/{ver}/{iteration}/{file_name}")
def download_direct(
    ws: str, pn: str, ver: str, iteration: int, file_name: str,
    current_user: Account = Depends(get_current_user),
):
    """几何体 GLB 直下（fullname 无 subType 段）。"""
    try:
        data = file_service.get_file_bytes(ws, pn, ver, iteration, None, file_name)
    except FileNotFoundError:
        raise HTTPException(404, "File not found")
    return Response(content=data, media_type="application/octet-stream")
