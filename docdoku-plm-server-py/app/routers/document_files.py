"""文档文件上传下载端点。"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import NotAllowedException
from app.models.auth import Account
from app.models.document import DocumentRevision
from app.services.document_manager import DocumentService

router = APIRouter()
svc = DocumentService()


def _check_doc_writable(db: Session, ws: str, doc_id: str, ver: str,
                        iteration: int, user_login: str) -> None:
    """工作区成员 + 签出用户匹配 + 最新迭代校验。"""
    is_member = db.execute(text(
        "SELECT COUNT(*) FROM userdata WHERE login=:l AND workspace_id=:w"
    ), {"l": user_login, "w": ws}).scalar()
    if not is_member:
        raise NotAllowedException("NotAllowedException4")
    dr = db.query(DocumentRevision).filter(
        DocumentRevision.workspace_id == ws,
        DocumentRevision.documentmaster_id == doc_id,
        DocumentRevision.version == ver,
    ).first()
    if dr is None:
        raise NotAllowedException("NotAllowedException4")
    if dr.checkout_user_login != user_login:
        raise NotAllowedException("NotAllowedException4")
    if dr.last_iteration_number != iteration:
        raise NotAllowedException("NotAllowedException4")


@router.post("/files/{ws}/documents/{doc_id}/{version}/{iteration}", status_code=201)
@router.post("/files/{ws}/documents/{doc_id}/{version}/{iteration}/",
             status_code=201, include_in_schema=False)
def upload(ws: str, doc_id: str, version: str, iteration: int,
           upload: UploadFile = File(...),
           current_user: Account = Depends(get_current_user),
           db: Session = Depends(get_db)):
    _check_doc_writable(db, ws, doc_id, version, iteration, current_user.login)
    data = upload.file.read()
    svc.save_file(db, ws, doc_id, version, iteration, upload.filename, data)
    return {"status": "uploaded"}


@router.get("/files/{ws}/documents/{doc_id}/{version}/{iteration}/{file_name}")
@router.get("/files/{ws}/documents/{doc_id}/{version}/{iteration}/{file_name}/", include_in_schema=False)
def download(ws: str, doc_id: str, version: str, iteration: int, file_name: str,
             current_user: Account = Depends(get_current_user)):
    try:
        data = svc.get_file_bytes(ws, doc_id, version, iteration, file_name)
    except FileNotFoundError:
        raise HTTPException(404, "File not found")
    return Response(content=data, media_type="application/octet-stream")

