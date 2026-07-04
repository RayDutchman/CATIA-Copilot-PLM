"""文件夹端点路由（FolderResource）。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.document_service import DocumentService

router = APIRouter()
svc = DocumentService()


@router.get("/workspaces/{ws}/folders")
def list_root(ws: str, current_user: Account = Depends(get_current_user),
              db: Session = Depends(get_db)):
    return [{"path": f.completepath, "name": f.completepath}
            for f in svc.list_folders(db, ws)]


@router.get("/workspaces/{ws}/folders/{folder_path:path}/folders")
def list_sub(ws: str, folder_path: str,
             current_user: Account = Depends(get_current_user),
             db: Session = Depends(get_db)):
    return [{"path": f.completepath, "name": f.completepath}
            for f in svc.list_folders(db, folder_path)]


@router.post("/workspaces/{ws}/folders", status_code=201)
def create_root(ws: str, body: dict,
                current_user: Account = Depends(get_current_user),
                db: Session = Depends(get_db)):
    name = body.get("name", "")
    f = svc.create_folder(db, ws, name)
    return {"path": f.completepath, "name": name}


@router.post("/workspaces/{ws}/folders/{parent_path:path}/folders", status_code=201)
def create_sub(ws: str, parent_path: str, body: dict,
               current_user: Account = Depends(get_current_user),
               db: Session = Depends(get_db)):
    name = body.get("name", "")
    f = svc.create_folder(db, parent_path, name)
    return {"path": f.completepath, "name": name}


@router.put("/workspaces/{ws}/folders/{folder_path:path}")
def rename_put(ws: str, folder_path: str, body: dict,
               current_user: Account = Depends(get_current_user),
               db: Session = Depends(get_db)):
    new_name = body.get("name", body.get("folderName", ""))
    svc.rename_folder(db, folder_path, new_name)
    return {"status": "renamed"}


@router.delete("/workspaces/{ws}/folders/{folder_path:path}")
def delete(ws: str, folder_path: str,
           current_user: Account = Depends(get_current_user),
           db: Session = Depends(get_db)):
    svc.delete_folder(db, folder_path)
    return {"status": "deleted"}


@router.get("/workspaces/{ws}/folders/{folder_id:path}/documents")
def list_folder_docs(ws: str, folder_id: str,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    from app.routers.documents import _doc_to_dict
    return [_doc_to_dict(r) for r in svc.list_documents_in_folder(db, ws, folder_id)]


@router.post("/workspaces/{ws}/folders/{folder_id:path}/documents", status_code=201)
def create_in_folder(ws: str, folder_id: str, body: dict,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    doc_id = body.get("reference", "")
    title = body.get("title", "")
    rev = svc.create_document(db, ws, doc_id, title,
                              current_user.login, folder_path=folder_id)
    from app.routers.documents import _doc_to_dict
    return _doc_to_dict(rev)
