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
from app.schemas.part import BinaryResourceDTO, StatusDTO
from datetime import datetime, timezone

router = APIRouter()
svc = ProductService()

CAD_WHITELIST = {"stp", "step", "igs", "iges", "stl", "off", "ply", "obj", "dae", "ifc"}


def _check_writable(db: Session, ws: str, pn: str, ver: str,
                    iteration: int, user_login: str) -> None:
    """签出用户 && 最新迭代，否则 NotAllowedException4。"""
    pr = svc.get_revision(db, ws, pn, ver)
    if pr.checkout_user_login != user_login or pr.last_iteration_number != iteration:
        raise NotAllowedException("NotAllowedException4")


@router.post("/files/{ws}/parts/{pn}/{ver}/{iteration}/nativecad",
             status_code=201, response_model=BinaryResourceDTO)
@router.post("/files/{ws}/parts/{pn}/{ver}/{iteration}/nativecad/",
             status_code=201, response_model=BinaryResourceDTO, include_in_schema=False)
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
    br = binary_storage.save_nativecad(db, ws, pn, ver, iteration, upload.filename, data)
    # Fix 2: 检查是否已有 pending Conversion，避免重复发送 Kafka
    existing = find_pending_conversion(db, ws, pn, ver)
    if existing:
        db.commit()
        return BinaryResourceDTO(
            fullName=br.full_name,
            name=upload.filename,
            contentLength=len(data),
            lastModified=br.last_modified,
        )
    svc.create_conversion(db, ws, pn, ver, iteration)
    db.commit()
    auth = request.headers.get("authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    send_conversion_order(ws, pn, ver, iteration, upload.filename, token)
    return BinaryResourceDTO(
        fullName=br.full_name,
        name=upload.filename,
        contentLength=len(data),
        lastModified=br.last_modified,
    )


@router.post("/files/{ws}/parts/{pn}/{ver}/{iteration}/attachedfiles",
             status_code=201, response_model=BinaryResourceDTO)
@router.post("/files/{ws}/parts/{pn}/{ver}/{iteration}/attachedfiles/",
             status_code=201, response_model=BinaryResourceDTO, include_in_schema=False)
def upload_attached(
    ws: str, pn: str, ver: str, iteration: int,
    upload: UploadFile = File(...),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_writable(db, ws, pn, ver, iteration, current_user.login)
    data = upload.file.read()
    br = binary_storage.save_attached(db, ws, pn, ver, iteration, upload.filename, data)
    db.commit()
    return BinaryResourceDTO(
        fullName=br.full_name,
        name=upload.filename,
        contentLength=len(data),
        lastModified=br.last_modified,
    )


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
    binary_storage.delete_part_file(db, ws, pn, ver, iteration,
                                      sub_type, file_name, current_user.login)


@router.put("/files/{ws}/parts/{pn}/{ver}/{iteration}/{sub_type}/{file_name}",
            status_code=200, response_model=StatusDTO)
@router.put("/files/{ws}/parts/{pn}/{ver}/{iteration}/{sub_type}/{file_name}/",
            status_code=200, response_model=StatusDTO, include_in_schema=False)
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
    result = binary_storage.rename_part_file(
        db, ws, pn, ver, iteration, sub_type,
        file_name, new_file_name, current_user.login,
    )
    return StatusDTO(status="renamed", message=result["name"])
def _file_headers(data: bytes, file_path: Path, file_name: str) -> dict:
    stat = file_path.stat()
    mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    return {
        "Content-Disposition": f'attachment; filename="{file_name}"',
        "Cache-Control": "max-age=86400",
        "Last-Modified": mtime.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        "ETag": f'"{file_name}_{len(data)}_{int(stat.st_mtime)}"',
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, HEAD",
        "Accept-Ranges": "bytes",
    }


def _parse_range_header(range_header: str, file_size: int) -> tuple[int, int] | None:
    """解析 Range 请求头，返回 (start, end) 或 None。"""
    import re
    if not range_header:
        return None
    m = re.match(r'^bytes=(\d+)-(\d*)$', range_header.strip())
    if not m:
        return None
    start = int(m.group(1))
    end_str = m.group(2)
    if end_str:
        end = int(end_str)
    else:
        end = file_size - 1
    if start > end or start >= file_size:
        return None
    end = min(end, file_size - 1)
    return (start, end)


@router.get("/files/{ws}/parts/{pn}/{ver}/{iteration}/{sub_type}/{file_name}",
            response_class=Response)
@router.get("/files/{ws}/parts/{pn}/{ver}/{iteration}/{sub_type}/{file_name}/",
            response_class=Response, include_in_schema=False)
def download_with_subtype(
    ws: str, pn: str, ver: str, iteration: int, sub_type: str, file_name: str,
    request: Request,
    current_user: Account = Depends(get_current_user),
):
    from app.services.vault import _vault_root, part_nativecad_path, part_attached_path
    if sub_type == "nativecad":
        file_path = part_nativecad_path(ws, pn, ver, iteration, file_name)
    else:
        file_path = part_attached_path(ws, pn, ver, iteration, file_name)
    try:
        data = binary_storage.get_file_bytes(ws, pn, ver, iteration, sub_type, file_name)
    except FileNotFoundError:
        raise HTTPException(404, "File not found")
    headers = _file_headers(data, file_path, file_name)
    range_header = request.headers.get("range", "")
    if range_header:
        file_size = len(data)
        parsed = _parse_range_header(range_header, file_size)
        if parsed:
            start, end = parsed
            chunk = data[start:end + 1]
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
            headers["Content-Length"] = str(len(chunk))
            return Response(content=chunk, status_code=206,
                            media_type="application/octet-stream", headers=headers)
        else:
            raise HTTPException(416, detail="Requested Range Not Satisfiable")
    return Response(content=data, media_type="application/octet-stream", headers=headers)


@router.get("/files/{ws}/parts/{pn}/{ver}/{iteration}/{file_name}",
            response_class=Response)
@router.get("/files/{ws}/parts/{pn}/{ver}/{iteration}/{file_name}/",
            response_class=Response, include_in_schema=False)
def download_direct(
    ws: str, pn: str, ver: str, iteration: int, file_name: str,
    request: Request,
    current_user: Account = Depends(get_current_user),
):
    """几何体 GLB 直下（fullname 无 subType 段）。"""
    from app.services.vault import _vault_root
    file_path = _vault_root() / ws / "parts" / pn / ver / str(iteration) / file_name
    try:
        data = binary_storage.get_file_bytes(ws, pn, ver, iteration, None, file_name)
    except FileNotFoundError:
        raise HTTPException(404, "File not found")
    headers = _file_headers(data, file_path, file_name)
    range_header = request.headers.get("range", "")
    if range_header:
        file_size = len(data)
        parsed = _parse_range_header(range_header, file_size)
        if parsed:
            start, end = parsed
            chunk = data[start:end + 1]
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
            headers["Content-Length"] = str(len(chunk))
            return Response(content=chunk, status_code=206,
                            media_type="application/octet-stream", headers=headers)
        else:
            raise HTTPException(416, detail="Requested Range Not Satisfiable")
    return Response(content=data, media_type="application/octet-stream", headers=headers)

