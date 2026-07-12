"""文件夹端点路由（FolderResource）。"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import AccessRightException
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
    new_parent = body.get("parentFolder", ws)
    svc.move_folder(db, ws, folder_id, new_parent, current_user.login)


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
    return [svc.build_revision_dto(db, r, current_user.login) for r in svc.list_documents_in_folder(db, ws, folder_id)]


@router.post("/workspaces/{ws}/folders/{folder_id:path}/documents", status_code=201)
@router.post("/workspaces/{ws}/folders/{folder_id:path}/documents/", status_code=201, include_in_schema=False)
def create_in_folder(ws: str, folder_id: str, body: dict,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    doc_id = body.get("reference", "")
    title = body.get("title", "")
    description = body.get("description", "")
    template_id = body.get("templateId")
    workflow_model_id = body.get("workflowModelId")
    acl = body.get("acl", {})
    role_mapping = body.get("roleMapping")
    user_entries = acl.get("userEntriesMap") if acl else None
    user_group_entries = acl.get("userGroupEntriesMap") if acl else None
    rev = svc.create_document(db, ws, doc_id, title,
                               current_user.login, folder_path=folder_id,
                               template_id=template_id,
                               workflow_model_id=workflow_model_id,
                               role_mapping=role_mapping)
    if description:
        rev.description = description
    if user_entries or user_group_entries:
        from app.services.factory.acl_factory import apply_acl
        acl_id = getattr(rev, "acl_id", None)
        new_acl_id = apply_acl(db, acl_id, user_entries, user_group_entries)
        if getattr(rev, "acl_id", None) != new_acl_id:
            rev.acl_id = new_acl_id
    db.commit()
    return svc.build_revision_dto(db, rev, current_user.login)
