"""零件模板端点（PartTemplateResource）。"""
from fastapi import APIRouter, Depends, Body
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.schemas.part import PartTemplateDTO, GeneratedIdDTO, AclIdDTO
from app.services.product_manager import ProductService
from app.services.factory.acl_factory import check_write_access

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
svc = ProductService()


@router.get("/workspaces/{workspace_id}/part-templates",
            response_model=list[PartTemplateDTO])
@router.get("/workspaces/{workspace_id}/part-templates/",
            response_model=list[PartTemplateDTO], include_in_schema=False)
def list_part_templates(workspace_id: str,
                        current_user: Account = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    return svc.list_part_templates(db, workspace_id)


@router.get("/workspaces/{workspace_id}/part-templates/{template_id}",
            response_model=PartTemplateDTO)
@router.get("/workspaces/{workspace_id}/part-templates/{template_id}/",
            response_model=PartTemplateDTO, include_in_schema=False)
def get_part_template(workspace_id: str, template_id: str,
                      current_user: Account = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    return svc.get_part_template(db, workspace_id, template_id)


@router.post("/workspaces/{workspace_id}/part-templates",
             status_code=201, response_model=PartTemplateDTO)
@router.post("/workspaces/{workspace_id}/part-templates/",
             status_code=201, response_model=PartTemplateDTO, include_in_schema=False)
def create_part_template(workspace_id: str,
                         body: dict = Body(...),
                         current_user: Account = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    check_write_access(db, None, current_user.login, False, workspace_id=workspace_id)
    return svc.create_part_template(db, workspace_id, body, current_user.login)


@router.put("/workspaces/{workspace_id}/part-templates/{template_id}",
            response_model=PartTemplateDTO)
@router.put("/workspaces/{workspace_id}/part-templates/{template_id}/",
            response_model=PartTemplateDTO, include_in_schema=False)
def update_part_template(workspace_id: str, template_id: str,
                         body: dict = Body(...),
                         current_user: Account = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    check_write_access(db, None, current_user.login, False, workspace_id=workspace_id)
    return svc.update_part_template(db, workspace_id, template_id, body)


@router.delete("/workspaces/{workspace_id}/part-templates/{template_id}", status_code=204)
@router.delete("/workspaces/{workspace_id}/part-templates/{template_id}/", status_code=204, include_in_schema=False)
def delete_part_template(workspace_id: str, template_id: str,
                         current_user: Account = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    check_write_access(db, None, current_user.login, False, workspace_id=workspace_id)
    svc.delete_part_template(db, workspace_id, template_id)
    return Response(status_code=204)


@router.get("/workspaces/{workspace_id}/part-templates/{template_id}/generate_id",
            response_model=GeneratedIdDTO)
@router.get("/workspaces/{workspace_id}/part-templates/{template_id}/generate_id/",
            response_model=GeneratedIdDTO, include_in_schema=False)
def generate_part_id(workspace_id: str, template_id: str,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    generated = svc.generate_part_template_id(db, workspace_id, template_id)
    return {"generatedId": generated}


@router.put("/workspaces/{workspace_id}/part-templates/{template_id}/acl",
            response_model=AclIdDTO)
@router.put("/workspaces/{workspace_id}/part-templates/{template_id}/acl/",
            response_model=AclIdDTO, include_in_schema=False)
def update_part_template_acl(workspace_id: str, template_id: str,
                             body: dict = Body(...),
                             current_user: Account = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    check_write_access(db, None, current_user.login, False, workspace_id=workspace_id)
    new_acl_id = svc.update_part_template_acl(db, workspace_id, template_id, body)
    return {"aclId": new_acl_id}
