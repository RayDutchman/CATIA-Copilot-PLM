"""文件夹端点路由（FolderResource）。"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import AccessRightException, EntityAlreadyExistsException, FolderNotFoundException
from app.models.auth import Account
from app.services.document_manager import DocumentService
from app.schemas.misc import FolderDTO, FolderStatusDTO

router = APIRouter()
svc = DocumentService()


def _check_workspace_write_access(db: Session, ws: str, login: str):
    """检查用户是否有工作区写权限，对齐 Java hasWorkspaceWriteAccess。"""
    from app.services.factory.acl_factory import check_write_access
    check_write_access(db, None, login, False, workspace_id=ws)


@router.get("/workspaces/{ws}/folders", response_model=List[FolderDTO])
@router.get("/workspaces/{ws}/folders/", include_in_schema=False)
def list_root(ws: str, current_user: Account = Depends(get_current_user),
              db: Session = Depends(get_db)):
    folders = svc.list_folders(db, ws)
    home_path = f"{ws}/~{current_user.login}"
    result = []
    for f in folders:
        is_home = f.completepath == home_path
        folder_name = f.completepath.split('/')[-1]
        # 过滤其他用户的主文件夹（~ 开头的文件夹是用户专属，不属于普通文件夹列表）
        if not is_home and folder_name.startswith("~"):
            continue
        result.append({
            "id": f"{ws}:{f.completepath}",
            "name": folder_name,
            "path": f.completepath, "home": is_home,
        })
    return result


@router.get("/workspaces/{ws}/folders/{folder_path:path}/folders", response_model=List[FolderDTO])
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


@router.put("/workspaces/{ws}/folders/{folder_id:path}/move", status_code=204)
@router.put("/workspaces/{ws}/folders/{folder_id:path}/move/", status_code=204, include_in_schema=False)
def move_folder(ws: str, folder_id: str, body: dict,
                current_user: Account = Depends(get_current_user),
                db: Session = Depends(get_db)):
    _check_workspace_write_access(db, ws, current_user.login)
    from app.models.document import Folder, DocumentRevision
    from fastapi import HTTPException
    folder = db.query(Folder).filter(Folder.completepath == folder_id).first()
    if not folder:
        raise FolderNotFoundException("FolderNotFoundException", folder_id)
    new_parent = body.get("parentFolder", ws)
    old_prefix = folder.completepath
    old_name = old_prefix.split('/')[-1]
    new_path = f"{new_parent}/{old_name}" if new_parent else old_name
    existing = db.query(Folder).filter(Folder.completepath == new_path).first()
    if existing:
        raise EntityAlreadyExistsException("FolderAlreadyExistsException", new_path)
    rows = db.query(Folder).filter(Folder.completepath.like(f"{old_prefix}%")).all()
    for f in rows:
        f.completepath = f.completepath.replace(old_prefix, new_path, 1)
        if f.parentfolder_completepath:
            f.parentfolder_completepath = f.parentfolder_completepath.replace(old_prefix, new_path, 1)
    docs = db.query(DocumentRevision).filter(
        DocumentRevision.location_completepath.like(f"{old_prefix}%")
    ).all()
    for doc in docs:
        doc.location_completepath = doc.location_completepath.replace(old_prefix, new_path, 1)
    db.commit()


@router.put("/workspaces/{ws}/folders/{folder_path:path}")
@router.put("/workspaces/{ws}/folders/{folder_path:path}/", include_in_schema=False)
def rename_put(ws: str, folder_path: str, body: dict,
               current_user: Account = Depends(get_current_user),
               db: Session = Depends(get_db)):
    new_name = body.get("name", body.get("folderName", ""))
    f = svc.rename_folder(db, folder_path, new_name)
    return {"id": f"{ws}:{f.completepath}", "path": f.completepath, "name": new_name}


@router.delete("/workspaces/{ws}/folders/{folder_path:path}", status_code=204)
@router.delete("/workspaces/{ws}/folders/{folder_path:path}/", status_code=204, include_in_schema=False)
def delete(ws: str, folder_path: str,
           current_user: Account = Depends(get_current_user),
           db: Session = Depends(get_db)):
    _check_workspace_write_access(db, ws, current_user.login)
    svc.delete_folder(db, folder_path, current_user.login)


@router.get("/workspaces/{ws}/folders/{folder_id:path}/documents")
@router.get("/workspaces/{ws}/folders/{folder_id:path}/documents/", include_in_schema=False)
def list_folder_docs(ws: str, folder_id: str,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    from app.routers.documents import _doc_to_dict
    return [_doc_to_dict(db, r, current_user.login) for r in svc.list_documents_in_folder(db, ws, folder_id)]


@router.post("/workspaces/{ws}/folders/{folder_id:path}/documents", status_code=201)
@router.post("/workspaces/{ws}/folders/{folder_id:path}/documents/", status_code=201, include_in_schema=False)
def create_in_folder(ws: str, folder_id: str, body: dict,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    doc_id = body.get("reference", "")
    title = body.get("title", "")
    template_id = body.get("templateId")
    workflow_model_id = body.get("workflowModelId")
    rev = svc.create_document(db, ws, doc_id, title,
                              current_user.login, folder_path=folder_id,
                              template_id=template_id,
                              workflow_model_id=workflow_model_id)
    from app.routers.documents import _doc_to_dict
    return _doc_to_dict(db, rev, current_user.login)

