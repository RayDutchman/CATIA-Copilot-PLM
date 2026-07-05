"""产品实例端点（ProductInstancesResource）。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.product_structure_service import ProductStructureService

router = APIRouter()
svc = ProductStructureService()


@router.get("/workspaces/{ws}/products/{ci_id}/instances")
def list_instances(ws: str, ci_id: str,
                   current_user: Account = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    return [{"serialNumber": i.serialnumber, "configurationItemId": i.configurationitem_id}
            for i in svc.list_instances(db, ws, ci_id)]


@router.post("/workspaces/{ws}/products/{ci_id}/instances", status_code=201)
@router.post("/workspaces/{ws}/products/{ci_id}/instances/", status_code=201, include_in_schema=False)
def create_instance(ws: str, ci_id: str, body: dict,
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    inst = svc.create_instance(db, ws, ci_id, body.get("serialNumber", ""),
                                body.get("baselineId", 0), current_user.login)
    return {"serialNumber": inst.serialnumber}


@router.delete("/workspaces/{ws}/products/{ci_id}/instances/{sn}")
def delete_instance(ws: str, ci_id: str, sn: str,
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    svc.delete_instance(db, ws, ci_id, sn)
    return {"status": "deleted"}
