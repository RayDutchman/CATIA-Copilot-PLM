"""文档文件上传下载端点。"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.document_service import DocumentService

router = APIRouter()
svc = DocumentService()


@router.post("/files/{ws}/documents/{doc_id}/{version}/{iteration}", status_code=201)
def upload(ws: str, doc_id: str, version: str, iteration: int,
           upload: UploadFile = File(...),
           current_user: Account = Depends(get_current_user),
           db: Session = Depends(get_db)):
    data = upload.file.read()
    svc.save_file(db, ws, doc_id, version, iteration, upload.filename, data)
    return {"status": "uploaded"}


@router.get("/files/{ws}/documents/{doc_id}/{version}/{iteration}/{file_name}")
def download(ws: str, doc_id: str, version: str, iteration: int, file_name: str,
             current_user: Account = Depends(get_current_user)):
    try:
        data = svc.get_file_bytes(ws, doc_id, version, iteration, file_name)
    except FileNotFoundError:
        raise HTTPException(404, "File not found")
    return Response(content=data, media_type="application/octet-stream")
