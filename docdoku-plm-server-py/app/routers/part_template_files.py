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
from sqlalchemy import text
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.models.part import BinaryResource
from app.services import vault as vault_svc

router = APIRouter()


def _template_file_path(ws: str, template_id: str, filename: str) -> Path:
    """返回零件模板附件的 vault 路径。"""
    return vault_svc._vault_root() / ws / "part-templates" / template_id / filename


def _full_name(ws: str, template_id: str, filename: str) -> str:
    return f"{ws}/part-templates/{template_id}/{filename}"


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


@router.post("/files/{ws}/part-templates/{template_id}", status_code=201)
@router.post("/files/{ws}/part-templates/{template_id}/", status_code=201, include_in_schema=False)
def upload_part_template_files(
    ws: str,
    template_id: str,
    uploads: List[UploadFile] = File(...),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传零件模板附件（multipart/form-data）。

    对标 Java PartTemplateBinaryResource.uploadPartTemplateFiles()。
    """
    saved = []
    for upload in uploads:
        fn = upload.filename
        if not fn:
            continue
        # NFC 规范化文件名
        import unicodedata
        fn = unicodedata.normalize("NFC", fn)

        data = upload.file.read()
        file_path = _template_file_path(ws, template_id, fn)
        vault_svc.write_file(file_path, data)

        full_name = _full_name(ws, template_id, fn)
        br = db.query(BinaryResource).filter(
            BinaryResource.full_name == full_name).first()
        now = datetime.utcnow()
        if br is None:
            br = BinaryResource(
                full_name=full_name,
                content_length=len(data),
                last_modified=now,
                dtype="BinaryResource",
            )
            db.add(br)
            db.flush()

        # 关联到 partmastertemplate_binres
        exists = db.execute(text(
            "SELECT 1 FROM partmastertemplate_binres "
            "WHERE workspace_id=:ws AND partmastertemplate_id=:tid "
            "AND attachedfile_fullname=:fn"
        ), {"ws": ws, "tid": template_id, "fn": full_name}).first()
        if exists is None:
            db.execute(text(
                "INSERT INTO partmastertemplate_binres "
                "(workspace_id, partmastertemplate_id, attachedfile_fullname) "
                "VALUES (:ws, :tid, :fn)"
            ), {"ws": ws, "tid": template_id, "fn": full_name})

        db.commit()
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
):
    """下载零件模板附件。

    对标 Java PartTemplateBinaryResource.downloadPartTemplateFile()。
    支持 HTTP Range 断点续传。（零件模板不支持格式转换）
    """
    file_path = _template_file_path(ws, template_id, file_name)
    try:
        data = vault_svc.read_file(file_path)
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
