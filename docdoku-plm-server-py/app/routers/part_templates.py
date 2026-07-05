"""零件模板端点（PartTemplateResource）。"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.models.part import PartMasterTemplate
from app.services.acl_helper import apply_acl

router = APIRouter(prefix="/docdoku-plm-server-rest/api")


@router.get("/workspaces/{workspace_id}/part-templates")
@router.get("/workspaces/{workspace_id}/part-templates/", include_in_schema=False)
def list_part_templates(workspace_id: str,
                        current_user: Account = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    templates = (
        db.query(PartMasterTemplate)
        .filter(PartMasterTemplate.workspace_id == workspace_id)
        .all()
    )
    result = []
    for t in templates:
        result.append({
            "id": t.id,
            "workspaceId": t.workspace_id,
            "mask": t.mask,
            "idGenerated": t.id_generated,
            "partType": t.part_type,
            "attributesLocked": t.attributes_locked,
            "authorLogin": t.author_login,
            "authorWorkspaceId": t.author_workspace_id,
            "creationDate": t.creation_date.isoformat() if t.creation_date else None,
            "modificationDate": t.modification_date.isoformat() if t.modification_date else None,
            "aclId": t.acl_id,
            "workflowModelId": t.workflowmodel_id,
        })
    return result


@router.get("/workspaces/{workspace_id}/part-templates/{template_id}")
@router.get("/workspaces/{workspace_id}/part-templates/{template_id}/", include_in_schema=False)
def get_part_template(workspace_id: str, template_id: str,
                      current_user: Account = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    t = (
        db.query(PartMasterTemplate)
        .filter(PartMasterTemplate.workspace_id == workspace_id,
                PartMasterTemplate.id == template_id)
        .first()
    )
    if t is None:
        raise HTTPException(404, f"Template {template_id} not found")
    return {
        "id": t.id,
        "workspaceId": t.workspace_id,
        "mask": t.mask,
        "idGenerated": t.id_generated,
        "partType": t.part_type,
        "attributesLocked": t.attributes_locked,
        "authorLogin": t.author_login,
        "authorWorkspaceId": t.author_workspace_id,
        "creationDate": t.creation_date.isoformat() if t.creation_date else None,
        "modificationDate": t.modification_date.isoformat() if t.modification_date else None,
        "aclId": t.acl_id,
        "workflowModelId": t.workflowmodel_id,
    }


@router.post("/workspaces/{workspace_id}/part-templates", status_code=201)
@router.post("/workspaces/{workspace_id}/part-templates/", status_code=201, include_in_schema=False)
def create_part_template(workspace_id: str,
                         body: dict = Body(...),
                         current_user: Account = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    t = PartMasterTemplate(
        id=body.get("id", ""),
        workspace_id=workspace_id,
        mask=body.get("mask", ""),
        id_generated=body.get("idGenerated", False),
        part_type=body.get("partType", ""),
        attributes_locked=body.get("attributesLocked", False),
        author_login=current_user.login,
        author_workspace_id=workspace_id,
        creation_date=datetime.utcnow(),
        modification_date=datetime.utcnow(),
        acl_id=body.get("aclId"),
        workflowmodel_id=body.get("workflowModelId"),
    )
    db.add(t)
    db.commit()
    return {
        "id": t.id,
        "workspaceId": t.workspace_id,
        "mask": t.mask,
        "idGenerated": t.id_generated,
        "partType": t.part_type,
        "attributesLocked": t.attributes_locked,
        "authorLogin": t.author_login,
        "authorWorkspaceId": t.author_workspace_id,
        "creationDate": t.creation_date.isoformat() if t.creation_date else None,
        "modificationDate": t.modification_date.isoformat() if t.modification_date else None,
        "aclId": t.acl_id,
        "workflowModelId": t.workflowmodel_id,
    }


@router.put("/workspaces/{workspace_id}/part-templates/{template_id}")
@router.put("/workspaces/{workspace_id}/part-templates/{template_id}/", include_in_schema=False)
def update_part_template(workspace_id: str, template_id: str,
                         body: dict = Body(...),
                         current_user: Account = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    t = (
        db.query(PartMasterTemplate)
        .filter(PartMasterTemplate.workspace_id == workspace_id,
                PartMasterTemplate.id == template_id)
        .first()
    )
    if t is None:
        raise HTTPException(404, f"Template {template_id} not found")
    if "mask" in body:
        t.mask = body["mask"]
    if "idGenerated" in body:
        t.id_generated = body["idGenerated"]
    if "partType" in body:
        t.part_type = body["partType"]
    if "attributesLocked" in body:
        t.attributes_locked = body["attributesLocked"]
    if "workflowModelId" in body:
        t.workflowmodel_id = body["workflowModelId"]
    t.modification_date = datetime.utcnow()
    db.commit()
    return {
        "id": t.id,
        "workspaceId": t.workspace_id,
        "mask": t.mask,
        "idGenerated": t.id_generated,
        "partType": t.part_type,
        "attributesLocked": t.attributes_locked,
        "authorLogin": t.author_login,
        "authorWorkspaceId": t.author_workspace_id,
        "creationDate": t.creation_date.isoformat() if t.creation_date else None,
        "modificationDate": t.modification_date.isoformat() if t.modification_date else None,
        "aclId": t.acl_id,
        "workflowModelId": t.workflowmodel_id,
    }


@router.delete("/workspaces/{workspace_id}/part-templates/{template_id}", status_code=204)
@router.delete("/workspaces/{workspace_id}/part-templates/{template_id}/", status_code=204, include_in_schema=False)
def delete_part_template(workspace_id: str, template_id: str,
                         current_user: Account = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    t = (
        db.query(PartMasterTemplate)
        .filter(PartMasterTemplate.workspace_id == workspace_id,
                PartMasterTemplate.id == template_id)
        .first()
    )
    if t is None:
        raise HTTPException(404, f"Template {template_id} not found")
    db.delete(t)
    db.commit()
    return Response(status_code=204)


@router.put("/workspaces/{workspace_id}/part-templates/{template_id}/acl")
@router.put("/workspaces/{workspace_id}/part-templates/{template_id}/acl/", include_in_schema=False)
def update_part_template_acl(workspace_id: str, template_id: str,
                             body: dict = Body(...),
                             current_user: Account = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    t = (
        db.query(PartMasterTemplate)
        .filter(PartMasterTemplate.workspace_id == workspace_id,
                PartMasterTemplate.id == template_id)
        .first()
    )
    if t is None:
        raise HTTPException(404, f"Template {template_id} not found")
    user_entries = body.get("userEntries", {})
    group_entries = body.get("groupEntries", {})
    new_acl_id = apply_acl(db, t.acl_id, user_entries, group_entries)
    if t.acl_id != new_acl_id:
        t.acl_id = new_acl_id
        db.commit()
    return {"aclId": new_acl_id}
