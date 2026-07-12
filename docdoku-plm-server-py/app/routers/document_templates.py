"""文档模板端点路由（DocumentTemplateResource）。"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.models.document import DocumentMasterTemplate
from app.services.document_manager import DocumentService
from app.services.factory.acl_factory import apply_acl
from app.schemas.document import DocumentTemplateDTO

router = APIRouter()
svc = DocumentService()


@router.get("/workspaces/{ws}/document-templates", response_model=List[DocumentTemplateDTO])
@router.get("/workspaces/{ws}/document-templates/", include_in_schema=False)
def list_templates(ws: str, current_user: Account = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    templates = svc.list_templates(db, ws)
    result = []
    for t in templates:
        author = None
        if t.author_login:
            acc = db.query(Account).filter(Account.login == t.author_login).first()
            author = {
                "login": t.author_login,
                "name": acc.name if acc else t.author_login,
                "email": acc.email if acc else None,
                "language": acc.language if acc else None,
                "workspaceId": t.workspace_id,
            }
        acl = None
        if t.acl_id:
            from app.models.security import ACL, AclUserEntry, AclUserGroupEntry
            acl_obj = db.query(ACL).filter(ACL.id == t.acl_id).first()
            user_entries = []
            group_entries = []
            if acl_obj:
                user_entries = db.query(AclUserEntry).filter(
                    AclUserEntry.acl_id == t.acl_id).all()
                group_entries = db.query(AclUserGroupEntry).filter(
                    AclUserGroupEntry.acl_id == t.acl_id).all()
            perm_map = {0: "FORBIDDEN", 1: "READ_ONLY", 2: "FULL_ACCESS"}
            acl = {
                "userEntries": [{"key": e.principal_login, "value": perm_map.get(e.permission, "FORBIDDEN")} for e in user_entries],
                "groupEntries": [{"key": e.principal_id, "value": perm_map.get(e.permission, "FORBIDDEN")} for e in group_entries],
                "userEntriesMap": {e.principal_login: perm_map.get(e.permission, "FORBIDDEN") for e in user_entries},
                "userGroupEntriesMap": {e.principal_id: perm_map.get(e.permission, "FORBIDDEN") for e in group_entries},
            }
        result.append({
            "id": t.id, "workspaceId": t.workspace_id,
            "documentType": t.document_type, "mask": t.mask,
            "idGenerated": t.id_generated,
            "attributesLocked": t.attributes_locked,
            "author": author or {},
            "acl": acl or {},
            "creationDate": str(t.creation_date) if t.creation_date else None,
            "attachedFiles": [],
            "attributeTemplates": [],
        })
    return result


@router.get("/workspaces/{ws}/document-templates/{template_id}", response_model=DocumentTemplateDTO)
@router.get("/workspaces/{ws}/document-templates/{template_id}/", include_in_schema=False)
def get_template(ws: str, template_id: str,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    t = svc.get_template(db, ws, template_id)
    author = None
    if t.author_login:
        acc = db.query(Account).filter(Account.login == t.author_login).first()
        author = {
            "login": t.author_login,
            "name": acc.name if acc else t.author_login,
            "email": acc.email if acc else None,
            "language": acc.language if acc else None,
            "workspaceId": t.workspace_id,
        }
    acl = None
    if t.acl_id:
        from app.models.security import ACL, AclUserEntry, AclUserGroupEntry
        acl_obj = db.query(ACL).filter(ACL.id == t.acl_id).first()
        user_entries = []
        group_entries = []
        if acl_obj:
            user_entries = db.query(AclUserEntry).filter(
                AclUserEntry.acl_id == t.acl_id).all()
            group_entries = db.query(AclUserGroupEntry).filter(
                AclUserGroupEntry.acl_id == t.acl_id).all()
        perm_map = {0: "FORBIDDEN", 1: "READ_ONLY", 2: "FULL_ACCESS"}
        acl = {
            "userEntries": [{"key": e.principal_login, "value": perm_map.get(e.permission, "FORBIDDEN")} for e in user_entries],
            "groupEntries": [{"key": e.principal_id, "value": perm_map.get(e.permission, "FORBIDDEN")} for e in group_entries],
            "userEntriesMap": {e.principal_login: perm_map.get(e.permission, "FORBIDDEN") for e in user_entries},
            "userGroupEntriesMap": {e.principal_id: perm_map.get(e.permission, "FORBIDDEN") for e in group_entries},
        }
    return {
        "id": t.id, "workspaceId": t.workspace_id,
        "documentType": t.document_type, "mask": t.mask,
        "idGenerated": t.id_generated,
        "attributesLocked": t.attributes_locked,
        "author": author or {}, "acl": acl or {},
        "creationDate": str(t.creation_date) if t.creation_date else None,
        "attachedFiles": [], "attributeTemplates": [],
    }


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
    t = svc.get_template(db, ws, template_id)
    for field in ("documentType", "mask", "idGenerated"):
        if field in body:
            col = "document_type" if field == "documentType" else (
                "mask" if field == "mask" else "id_generated")
            setattr(t, col, body[field])
    if "workflowModelId" in body:
        t.workflowmodel_id = body["workflowModelId"]
    if "attributeTemplates" in body:
        # 先删除旧的属性模板关联
        db.execute(sql_text(
            "DELETE FROM documentmastertemplate_attr "
            "WHERE workspace_id=:ws AND documentmastertemplate_id=:tid"
        ), {"ws": ws, "tid": template_id})
        # 再插入新的属性模板
        for order, attr in enumerate(body["attributeTemplates"]):
            attr_name = attr.get("name", "")
            attr_dtype = attr.get("dtype", "InstanceTextAttribute")
            attr_mandatory = attr.get("mandatory", False)
            attr_locked = attr.get("locked", False)
            attr_type = attr.get("attributeType", 0)
            lov_name = attr.get("lovName")
            lov_ws = attr.get("lovWorkspaceId")
            result = db.execute(sql_text(
                "INSERT INTO instanceattributetemplate "
                "(dtype, name, mandatory, locked, attributetype, lov_name, lov_workspace_id) "
                "VALUES (:dtype, :name, :mand, :locked, :atype, :lovn, :lovw) RETURNING id"
            ), {"dtype": attr_dtype, "name": attr_name, "mand": attr_mandatory,
                "locked": attr_locked, "atype": attr_type,
                "lovn": lov_name, "lovw": lov_ws})
            attr_id = result.fetchone()[0]
            db.execute(sql_text(
                "INSERT INTO documentmastertemplate_attr "
                "(workspace_id, documentmastertemplate_id, instanceattributetemplate_id, attr_order) "
                "VALUES (:ws, :tid, :aid, :ord)"
            ), {"ws": ws, "tid": template_id, "aid": attr_id, "ord": order})
    if "lovs" in body or "LOVs" in body:
        pass  # 暂存 LOVs
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

