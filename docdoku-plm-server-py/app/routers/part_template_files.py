"""零件模板文件上传/下载端点（PartTemplateBinaryResource）。

POST /files/{ws}/part-templates/{templateId}
GET  /files/{ws}/part-templates/{templateId}/{fileName}
"""
from pathlib import Path
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, Request, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services import vault as vault_svc

router = APIRouter()


def _file_headers(data: bytes, file_path: Path, file_name: str) -> dict:
    try:
        stat = file_path.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        last_mod = mtime.strftime("%a, %d %b %Y %H:%M:%S GMT")
        etag = f'"{file_name}_{len(data)}_{int(stat.st_mtime)}"'
    except (FileNotFoundError, OSError):
        last_mod = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        etag = f'"{file_name}_{len(data)}"'
    return {
        "Content-Disposition": f'attachment; filename="{file_name}"',
        "Cache-Control": "no-cache",
        "Last-Modified": last_mod,
        "ETag": etag,
    }


def _parse_range(range_header: str, file_size: int) -> tuple[int, int] | None:
    import re
    m = re.match(r'^bytes=(\d+)-(\d*)$', range_header.strip())
    if not m:
        return None
    start = int(m.group(1))
    end = int(m.group(2)) if m.group(2) else file_size - 1
    if start > end or start >= file_size:
        return None
    return (start, min(end, file_size - 1))


@router.post("/files/{ws}/part-templates/{template_id}", status_code=201)
@router.post("/files/{ws}/part-templates/{template_id}/", status_code=201, include_in_schema=False)
def upload_part_template_files(
    ws: str,
    template_id: str,
    uploads: List[UploadFile] = File(...),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传零件模板附件。对标 Java PartTemplateBinaryResource.uploadPartTemplateFiles()。"""
    from app.services.product_manager import product_service
    saved = []
    for upload in uploads:
        fn = upload.filename
        if not fn:
            continue
        data = upload.file.read()
        product_service.upload_template_file(db, ws, template_id, fn, data)
        saved.append(fn)
    if not saved:
        raise HTTPException(400, "No valid files uploaded")
    if len(saved) == 1:
        return Response(status_code=201, content=saved[0], media_type="text/plain")
    return Response(status_code=204)


@router.get("/files/{ws}/part-templates/{template_id}/{file_name}")
@router.get("/files/{ws}/part-templates/{template_id}/{file_name}/", include_in_schema=False)
def download_part_template_file(
    ws: str,
    template_id: str,
    file_name: str,
    request: Request,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """下载零件模板附件。对标 Java PartTemplateBinaryResource.downloadPartTemplateFile()。"""
    from app.services.product_manager import product_service
    try:
        data, file_path = product_service.read_template_file(db, ws, template_id, file_name)
    except FileNotFoundError:
        raise HTTPException(404, "File not found")

    headers = _file_headers(data, file_path, file_name)
    range_header = request.headers.get("range", "")
    if range_header:
        file_size = len(data)
        parsed = _parse_range(range_header, file_size)
        if parsed:
            start, end = parsed
            chunk = data[start:end + 1]
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
            headers["Content-Length"] = str(len(chunk))
            return Response(content=chunk, status_code=206,
                            media_type="application/octet-stream", headers=headers)
        raise HTTPException(416, "Requested Range Not Satisfiable")
    return Response(content=data, media_type="application/octet-stream", headers=headers)


@router.delete("/files/{ws}/part-templates/{template_id}/{file_name}", status_code=204)
@router.delete("/files/{ws}/part-templates/{template_id}/{file_name}/", status_code=204, include_in_schema=False)
def remove_part_template_file(
    ws: str,
    template_id: str,
    file_name: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除零件模板附件（对标 Java PartTemplateBinaryResource.removeAttachedFileFromPartTemplate）。"""
    from app.services.product_manager import product_service
    product_service.remove_template_file(db, ws, template_id, file_name)
    return Response(status_code=204)


@router.put("/files/{ws}/part-templates/{template_id}/{file_name}")
@router.put("/files/{ws}/part-templates/{template_id}/{file_name}/", include_in_schema=False)
def rename_part_template_file(
    ws: str,
    template_id: str,
    file_name: str,
    body: dict,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """重命名零件模板附件（对标 Java PartTemplateBinaryResource.renameAttachedFileInPartTemplate）。"""
    new_file_name = body.get("fileName")
    if not new_file_name:
        raise HTTPException(400, "fileName is required")
    from app.services.product_manager import product_service
    product_service.rename_template_file(db, ws, template_id, file_name, new_file_name)
    return {"name": new_file_name}
