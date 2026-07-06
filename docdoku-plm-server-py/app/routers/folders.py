"""文件夹端点路由（FolderResource）。"""
from fastapi import APIRouter, Depends
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import AccessRightException
from app.models.auth import Account
from app.services.document_manager import DocumentService

router = APIRouter()
svc = DocumentService()


def _check_workspace_write_access(db: Session, ws: str, login: str):
    """检查用户是否有工作区写权限。"""
    row = db.execute(sql_text(
        "SELECT 1 FROM userdata WHERE login = :l AND workspace_id = :w"
    ), {"l": login, "w": ws}).first()
    if not row:
        raise AccessRightException("AccessRightException")


@router.get("/workspaces/{ws}/folders")
@router.get("/workspaces/{ws}/folders/", include_in_schema=False)
def list_root(ws: str, current_user: Account = Depends(get_current_user),
              db: Session = Depends(get_db)):
    folders = svc.list_folders(db, ws)
    # Payara 格式: id="ws:folderName", name=folderName, path=completePath
    return [{"id": f"{ws}:{f.completepath.split('/')[-1] if '/' in f.completepath else f.completepath}",
             "name": f.completepath.split('/')[-1],
             "path": f.completepath, "home": False} for f in folders]


@router.get("/workspaces/{ws}/folders/{folder_path:path}/folders")
@router.get("/workspaces/{ws}/folders/{folder_path:path}/folders/", include_in_schema=False)
@router.get("/workspaces/{ws}/folders/{folder_path:path}/folders/",
            include_in_schema=False)
def list_sub(ws: str, folder_path: str,
             current_user: Account = Depends(get_current_user),
             db: Session = Depends(get_db)):
    folders = svc.list_folders(db, ws, folder_path)
    return [{"id": f"{ws}:{f.completepath}", "name": f.completepath.split('/')[-1],
             "path": f.completepath, "home": False} for f in folders]


@router.post("/workspaces/{ws}/folders", status_code=201)
@router.post("/workspaces/{ws}/folders/", status_code=201, include_in_schema=False)
def create_root(ws: str, body: dict,
                current_user: Account = Depends(get_current_user),
                db: Session = Depends(get_db)):
    _check_workspace_write_access(db, ws, current_user.login)
    name = body.get("name", "")
    f = svc.create_folder(db, ws, name)
    return {"path": f.completepath, "name": name}


@router.post("/workspaces/{ws}/folders/{parent_path:path}/folders", status_code=201)
@router.post("/workspaces/{ws}/folders/{parent_path:path}/folders/", status_code=201, include_in_schema=False)
def create_sub(ws: str, parent_path: str, body: dict,
               current_user: Account = Depends(get_current_user),
               db: Session = Depends(get_db)):
    _check_workspace_write_access(db, ws, current_user.login)
    name = body.get("name", "")
    f = svc.create_folder(db, parent_path, name)
    return {"path": f.completepath, "name": name}


@router.put("/workspaces/{ws}/folders/{folder_path:path}")
@router.put("/workspaces/{ws}/folders/{folder_path:path}/", include_in_schema=False)
def rename_put(ws: str, folder_path: str, body: dict,
               current_user: Account = Depends(get_current_user),
               db: Session = Depends(get_db)):
    new_name = body.get("name", body.get("folderName", ""))
    svc.rename_folder(db, folder_path, new_name)
    return {"status": "renamed"}


@router.delete("/workspaces/{ws}/folders/{folder_path:path}")
@router.delete("/workspaces/{ws}/folders/{folder_path:path}/", include_in_schema=False)
def delete(ws: str, folder_path: str,
           current_user: Account = Depends(get_current_user),
           db: Session = Depends(get_db)):
    _check_workspace_write_access(db, ws, current_user.login)
    svc.delete_folder(db, folder_path, current_user.login)
    return {"status": "deleted"}


@router.get("/workspaces/{ws}/folders/{folder_id:path}/documents")
@router.get("/workspaces/{ws}/folders/{folder_id:path}/documents/", include_in_schema=False)
def list_folder_docs(ws: str, folder_id: str,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    from app.routers.documents import _doc_to_dict
    return [_doc_to_dict(r) for r in svc.list_documents_in_folder(db, ws, folder_id)]


@router.post("/workspaces/{ws}/folders/{folder_id:path}/documents", status_code=201)
@router.post("/workspaces/{ws}/folders/{folder_id:path}/documents/", status_code=201, include_in_schema=False)
def create_in_folder(ws: str, folder_id: str, body: dict,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    doc_id = body.get("reference", "")
    title = body.get("title", "")
    rev = svc.create_document(db, ws, doc_id, title,
                              current_user.login, folder_path=folder_id)
    from app.routers.documents import _doc_to_dict
    return _doc_to_dict(rev)

