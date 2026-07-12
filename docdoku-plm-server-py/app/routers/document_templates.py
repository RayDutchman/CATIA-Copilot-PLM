"""文档模板端点路由（DocumentTemplateResource）。"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.document_manager import DocumentService
from app.schemas.document import DocumentTemplateDTO

router = APIRouter()
svc = DocumentService()


@router.get("/workspaces/{ws}/document-templates", response_model=List[DocumentTemplateDTO])
@router.get("/workspaces/{ws}/document-templates/", include_in_schema=False)
def list_templates(ws: str, current_user: Account = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    return svc.list_templates_dto(db, ws)


@router.get("/workspaces/{ws}/document-templates/{template_id}", response_model=DocumentTemplateDTO)
@router.get("/workspaces/{ws}/document-templates/{template_id}/", include_in_schema=False)
def get_template(ws: str, template_id: str,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    return svc.get_template_dto(db, ws, template_id)


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
        attributes_locked=body.get("attributesLocked", False),
        user_login=current_user.login,
        workflow_model_id=body.get("workflowModelId"),
        attribute_templates=body.get("attributeTemplates", []))
    return {"id": t.id, "workspaceId": t.workspace_id}


@router.put("/workspaces/{ws}/document-templates/{template_id}")
def update(ws: str, template_id: str, body: dict,
           current_user: Account = Depends(get_current_user),
           db: Session = Depends(get_db)):
    return svc.update_template_with_attrs(db, ws, template_id, body)


@router.delete("/workspaces/{ws}/document-templates/{template_id}")
def delete(ws: str, template_id: str,
           current_user: Account = Depends(get_current_user),
           db: Session = Depends(get_db)):
    svc.delete_template(db, ws, template_id)
    return {"status": "deleted"}


@router.get("/workspaces/{ws}/document-templates/{template_id}/generate_id")
@router.get("/workspaces/{ws}/document-templates/{template_id}/generate_id/", include_in_schema=False)
def generate_id(ws: str, template_id: str,
                current_user: Account = Depends(get_current_user),
                db: Session = Depends(get_db)):
    import re
    tpl = svc.get_template(db, ws, template_id)
    mask = tpl.mask or ""
    if not tpl.id_generated:
        return {"generateId": ""}
    if mask:
        prefix = re.sub(r'\{[^}]*\}', '', mask)
        seq_part = re.search(r'\{(.*?)\}', mask)
        seq_fmt = seq_part.group(1) if seq_part else "001"
        like_pattern = re.escape(prefix) + '%'
    else:
        like_pattern = f"{template_id}-%"
    from sqlalchemy import text as sql_text
    rows = db.execute(sql_text(
        "SELECT id FROM documentmaster WHERE workspace_id=:ws AND id LIKE :pat"
    ), {"ws": ws, "pat": like_pattern}).fetchall()
    max_seq = 0
    for r in rows:
        existing_id = r[0]
        if mask and prefix:
            seq_str = existing_id[len(prefix):]
        else:
            seq_str = existing_id[len(template_id) + 1:]
        try:
            seq_num = int(seq_str)
            max_seq = max(max_seq, seq_num)
        except ValueError:
            pass
    next_seq = max_seq + 1
    if mask:
        next_id = re.sub(r'\{[^}]*\}', str(next_seq).zfill(len(seq_fmt) if seq_fmt.isdigit() else len(seq_fmt)), mask)
    else:
        next_id = f"{template_id}-{next_seq:03d}"
    return {"generateId": next_id}


@router.put("/workspaces/{ws}/document-templates/{template_id}/acl")
@router.put("/workspaces/{ws}/document-templates/{template_id}/acl/", include_in_schema=False)
def update_template_acl(ws: str, template_id: str, body: dict,
                        db: Session = Depends(get_db),
                        current_user: Account = Depends(get_current_user)):
    new_acl_id = svc.update_doc_template_acl(db, ws, template_id, body)
    return {"aclId": new_acl_id}
