"""文档模板端点路由（DocumentTemplateResource）。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.models.document import DocumentMasterTemplate
from app.services.document_service import DocumentService
from app.services.acl_helper import apply_acl

router = APIRouter()
svc = DocumentService()


@router.get("/workspaces/{ws}/document-templates")
def list_templates(ws: str, current_user: Account = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    templates = svc.list_templates(db, ws)
    return [{"id": t.id, "workspaceId": t.workspace_id,
             "documentType": t.document_type, "mask": t.mask,
             "idGenerated": t.id_generated, "attributesLocked": t.attributes_locked}
            for t in templates]


@router.get("/workspaces/{ws}/document-templates/{template_id}")
def get_template(ws: str, template_id: str,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    t = svc.get_template(db, ws, template_id)
    return {"id": t.id, "workspaceId": t.workspace_id,
            "documentType": t.document_type, "mask": t.mask,
            "idGenerated": t.id_generated}


@router.post("/workspaces/{ws}/document-templates", status_code=201)
def create(ws: str, body: dict,
           current_user: Account = Depends(get_current_user),
           db: Session = Depends(get_db)):
    t = svc.create_template(
        db, ws,
        template_id=body.get("reference", ""),
        document_type=body.get("documentType", ""),
        mask=body.get("mask", ""),
        id_generated=body.get("idGenerated", False),
        user_login=current_user.login)
    return {"id": t.id, "workspaceId": t.workspace_id}


@router.put("/workspaces/{ws}/document-templates/{template_id}")
def update(ws: str, template_id: str, body: dict,
           current_user: Account = Depends(get_current_user),
           db: Session = Depends(get_db)):
    t = svc.get_template(db, ws, template_id)
    for field in ("documentType", "mask", "idGenerated"):
        if field in body:
            col = "document_type" if field == "documentType" else (
                "mask" if field == "mask" else "id_generated")
            setattr(t, col, body[field])
    from datetime import datetime
    t.modification_date = datetime.utcnow()
    db.commit()
    return {"id": t.id, "status": "updated"}


@router.delete("/workspaces/{ws}/document-templates/{template_id}")
def delete(ws: str, template_id: str,
           current_user: Account = Depends(get_current_user),
           db: Session = Depends(get_db)):
    svc.delete_template(db, ws, template_id)
    return {"status": "deleted"}


@router.put("/workspaces/{ws}/document-templates/{template_id}/acl")
@router.put("/workspaces/{ws}/document-templates/{template_id}/acl/", include_in_schema=False)
def update_template_acl(ws: str, template_id: str, body: dict,
                        db: Session = Depends(get_db),
                        current_user: Account = Depends(get_current_user)):
    tpl = db.query(DocumentMasterTemplate).filter(
        DocumentMasterTemplate.workspace_id == ws,
        DocumentMasterTemplate.id == template_id,
    ).first()
    if not tpl:
        from app.core.exceptions import EntityNotFoundException
        raise EntityNotFoundException("DocumentMasterTemplateNotFoundException", template_id)
    acl_id = getattr(tpl, "acl_id", None)
    new_acl_id = apply_acl(db, acl_id, body.get("userEntries", {}), body.get("groupEntries", {}))
    if tpl.acl_id != new_acl_id:
        tpl.acl_id = new_acl_id
        db.commit()
    return {"aclId": new_acl_id}
