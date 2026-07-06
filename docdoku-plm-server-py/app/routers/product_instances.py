"""产品实例端点（ProductInstancesResource）。"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.product_structure import ProductStructureService
from app.schemas.product import ProductInstanceDTO, ProductInstanceIterationDTO

router = APIRouter()
svc = ProductStructureService()


def _get_user(db: Session, login: str, ws: str) -> dict:
    if not login:
        return {"login": "", "name": "", "email": None, "language": None, "workspaceId": ws}
    acc = db.query(Account).filter(Account.login == login).first()
    return {
        "login": login, "name": acc.name if acc else login,
        "email": acc.email if acc else None,
        "language": acc.language if acc else None,
        "workspaceId": ws,
    }


@router.get("/workspaces/{ws}/products/{ci_id}/instances", response_model=List[ProductInstanceDTO])
@router.get("/workspaces/{ws}/products/{ci_id}/instances/", include_in_schema=False)
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


@router.put("/workspaces/{ws}/products/{ci_id}/instances/{sn}")
@router.put("/workspaces/{ws}/products/{ci_id}/instances/{sn}/", include_in_schema=False)
def update_instance(ws: str, ci_id: str, sn: str, body: dict,
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    from app.models.product import ProductInstanceMaster, ProductInstanceIteration
    inst = db.query(ProductInstanceMaster).filter(
        ProductInstanceMaster.workspace_id == ws,
        ProductInstanceMaster.configurationitem_id == ci_id,
        ProductInstanceMaster.serialnumber == sn,
    ).first()
    if not inst:
        raise HTTPException(404, "Instance not found")
    last_it = db.query(ProductInstanceIteration).filter(
        ProductInstanceIteration.workspace_id == ws,
        ProductInstanceIteration.configurationitem_id == ci_id,
        ProductInstanceIteration.prdinstancemaster_serialnumber == sn,
    ).order_by(ProductInstanceIteration.iteration.desc()).first()
    if last_it and "description" in body:
        last_it.iteration_note = body["description"]
    if "linkedDocuments" in body and last_it:
        db.execute(sql_text(
            "DELETE FROM productinstanceiteration_documentlink "
            "WHERE workspace_id=:ws AND configurationitem_id=:ci "
            "AND prdinstancemaster_serialnumber=:sn AND iteration=:it"
        ), {"ws": ws, "ci": ci_id, "sn": sn, "it": last_it.iteration})
        for dl in body["linkedDocuments"]:
            dm_id = dl.get("documentMasterId", "")
            ver = dl.get("version", "")
            iter_num = dl.get("iteration", 1)
            db.execute(sql_text(
                "INSERT INTO productinstanceiteration_documentlink "
                "(workspace_id, configurationitem_id, prdinstancemaster_serialnumber, "
                "iteration, target_workspace_id, target_documentmaster_id, "
                "target_docrevision_version, target_iteration, commentdata) "
                "VALUES (:ws, :ci, :sn, :it, :tws, :dm, :ver, :iter, :comment)"
            ), {"ws": ws, "ci": ci_id, "sn": sn, "it": last_it.iteration,
                "tws": ws, "dm": dm_id, "ver": ver, "iter": iter_num,
                "comment": dl.get("comment", "")})
    db.commit()
    return {"serialNumber": inst.serialnumber}


@router.get("/workspaces/{ws}/products/{ci_id}/instances/{sn}/iterations", response_model=List[ProductInstanceIterationDTO])
@router.get("/workspaces/{ws}/products/{ci_id}/instances/{sn}/iterations/", include_in_schema=False)
def list_instance_iterations(ws: str, ci_id: str, sn: str,
                              current_user: Account = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    from app.models.product import ProductInstanceIteration
    iterations = db.query(ProductInstanceIteration).filter(
        ProductInstanceIteration.workspace_id == ws,
        ProductInstanceIteration.configurationitem_id == ci_id,
        ProductInstanceIteration.prdinstancemaster_serialnumber == sn,
    ).order_by(ProductInstanceIteration.iteration).all()
    return [
        {
            "iteration": it.iteration,
            "iterationNote": it.iteration_note,
            "creationDate": it.creation_date.isoformat() + "Z" if it.creation_date else None,
            "modificationDate": it.modification_date.isoformat() + "Z" if it.modification_date else None,
            "author": _get_user(db, it.author_login or "", ws),
            "productBaselineId": it.productbaseline_id,
        }
        for it in iterations
    ]


@router.get("/workspaces/{ws}/products/{ci_id}/instances/{sn}/iterations/{it}")
@router.get("/workspaces/{ws}/products/{ci_id}/instances/{sn}/iterations/{it}/", include_in_schema=False)
def get_instance_iteration(ws: str, ci_id: str, sn: str, it: int,
                            current_user: Account = Depends(get_current_user),
                            db: Session = Depends(get_db)):
    from app.models.product import ProductInstanceIteration
    iteration = db.query(ProductInstanceIteration).filter(
        ProductInstanceIteration.workspace_id == ws,
        ProductInstanceIteration.configurationitem_id == ci_id,
        ProductInstanceIteration.prdinstancemaster_serialnumber == sn,
        ProductInstanceIteration.iteration == it,
    ).first()
    if not iteration:
        raise HTTPException(404, "Iteration not found")
    doc_rows = db.execute(sql_text(
        "SELECT dl.id, dl.target_workspace_id, dl.target_documentmaster_id, "
        "dl.target_docrevision_version, dl.commentdata "
        "FROM productinstanceiteration_documentlink pidl "
        "JOIN documentlink dl ON dl.id = pidl.documentlink_id "
        "WHERE pidl.workspace_id=:ws AND pidl.configurationitem_id=:ci "
        "AND pidl.prdinstancemaster_serialnumber=:sn AND pidl.iteration=:it"
    ), {"ws": ws, "ci": ci_id, "sn": sn, "it": it}).fetchall()
    return {
        "iteration": iteration.iteration,
        "iterationNote": iteration.iteration_note,
        "creationDate": iteration.creation_date.isoformat() + "Z" if iteration.creation_date else None,
        "modificationDate": iteration.modification_date.isoformat() + "Z" if iteration.modification_date else None,
        "author": _get_user(db, iteration.author_login or "", ws),
        "productBaselineId": iteration.productbaseline_id,
        "linkedDocuments": [
            {"id": r[0], "workspaceId": r[1], "documentMasterId": r[2],
             "version": r[3], "commentLink": r[4]}
            for r in doc_rows
        ],
    }


@router.delete("/workspaces/{ws}/products/{ci_id}/instances/{sn}")
def delete_instance(ws: str, ci_id: str, sn: str,
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    svc.delete_instance(db, ws, ci_id, sn)
    return {"status": "deleted"}


@router.put("/workspaces/{ws}/products/{ci_id}/instances/{sn}/acl")
def update_instance_acl(ws: str, ci_id: str, sn: str, body: dict,
                        db: Session = Depends(get_db),
                        current_user: Account = Depends(get_current_user)):
    from app.services.acl_helper import apply_acl
    from app.models.product import ProductInstanceMaster
    inst = db.query(ProductInstanceMaster).filter(
        ProductInstanceMaster.workspace_id == ws,
        ProductInstanceMaster.configurationitem_id == ci_id,
        ProductInstanceMaster.serialnumber == sn,
    ).first()
    if not inst:
        raise HTTPException(404, "Instance not found")
    user_entries = body.get("userEntries", {})
    group_entries = body.get("groupEntries", {})
    if not user_entries and not group_entries:
        inst.acl_id = None
        db.commit()
        return {"aclId": None}
    new_acl_id = apply_acl(db, inst.acl_id, user_entries, group_entries)
    inst.acl_id = new_acl_id
    db.commit()
    return {"aclId": new_acl_id}


@router.put("/workspaces/{ws}/products/{ci_id}/instances/{sn}/rebase", status_code=204)
def rebase_instance(ws: str, ci_id: str, sn: str,
                    body: dict = None,
                    current_user: Account = Depends(get_current_user)):
    from fastapi.responses import Response
    return Response(status_code=204)

