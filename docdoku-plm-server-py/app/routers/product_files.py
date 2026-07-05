"""产品实例文件端点（ProductInstanceBinaryResource）。"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services import vault as vault_svc
from datetime import datetime, timezone

router = APIRouter()


@router.post("/files/{ws}/products/{ci_id}/instances/{sn}/iterations/{it}", status_code=201)
@router.post("/files/{ws}/products/{ci_id}/instances/{sn}/iterations/{it}/", status_code=201, include_in_schema=False)
def upload(ws: str, ci_id: str, sn: str, it: int,
           upload: UploadFile = File(...),
           current_user: Account = Depends(get_current_user),
           db: Session = Depends(get_db)):
    data = upload.file.read()
    path = vault_svc._vault_root() / ws / "products" / ci_id / "instances" / sn / "iterations" / str(it) / upload.filename
    vault_svc.write_file(path, data)
    return {"status": "uploaded"}


@router.get("/files/{ws}/products/{ci_id}/instances/{sn}/iterations/{it}/{fn}")
@router.get("/files/{ws}/products/{ci_id}/instances/{sn}/iterations/{it}/{fn}/", include_in_schema=False)
def download(ws: str, ci_id: str, sn: str, it: int, fn: str,
             current_user: Account = Depends(get_current_user)):
    try:
        path = vault_svc._vault_root() / ws / "products" / ci_id / "instances" / sn / "iterations" / str(it) / fn
        data = vault_svc.read_file(path)
    except FileNotFoundError:
        raise HTTPException(404, "File not found")
    return Response(content=data, media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{fn}"',
            "Cache-Control": "max-age=86400",
            "Last-Modified": datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT"),
            "ETag": f'"{fn}_{len(data)}"',
        })

