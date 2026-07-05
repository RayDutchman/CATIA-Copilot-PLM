"""产品端点路由（ProductResource + Configurations + Baselines）。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.product_structure_service import ProductStructureService

router = APIRouter()
svc = ProductStructureService()


@router.get("/workspaces/{ws}/products")
def list_cis(ws: str, current_user: Account = Depends(get_current_user),
             db: Session = Depends(get_db)):
    cis = svc.list_cis(db, ws)
    return [{"id": c.id, "workspaceId": c.workspace_id,
             "description": c.description,
             "partNumber": c.partmaster_partnumber} for c in cis]


@router.get("/workspaces/{ws}/products/numbers")
def search_ci_numbers(ws: str, q: str = Query(""),
                      current_user: Account = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    cis = svc.search_numbers(db, ws, q)
    return [c.id for c in cis]


@router.post("/workspaces/{ws}/products", status_code=201)
@router.post("/workspaces/{ws}/products/", status_code=201, include_in_schema=False)
def create_ci(ws: str, body: dict,
              current_user: Account = Depends(get_current_user),
              db: Session = Depends(get_db)):
    ci_id = body.get("id", body.get("reference", ""))
    desc = body.get("description", "")
    part = body.get("designItemNumber", body.get("partNumber", body.get("partMasterNumber", "")))
    ci = svc.create_ci(db, ws, ci_id, desc, part, current_user.login)
    return {"id": ci.id, "workspaceId": ci.workspace_id,
            "description": ci.description, "partNumber": ci.partmaster_partnumber}


@router.get("/workspaces/{ws}/products/{ci_id}")
def get_ci(ws: str, ci_id: str,
           current_user: Account = Depends(get_current_user),
           db: Session = Depends(get_db)):
    ci = svc.get_ci(db, ws, ci_id)
    return {"id": ci.id, "workspaceId": ci.workspace_id,
            "description": ci.description, "partNumber": ci.partmaster_partnumber}


@router.delete("/workspaces/{ws}/products/{ci_id}")
def delete_ci(ws: str, ci_id: str,
              current_user: Account = Depends(get_current_user),
              db: Session = Depends(get_db)):
    svc.delete_ci(db, ws, ci_id)
    return {"status": "deleted"}


@router.get("/workspaces/{ws}/products/{ci_id}/filter")
def filter_structure(ws: str, ci_id: str,
                     configSpec: str = Query(None), path: str = Query(None),
                     depth: int = Query(None),
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    """返回递归 ComponentDTO 对象（非数组），对接 Payara filterProductStructure 响应。"""
    result = svc.filter_product_structure(db, ws, ci_id, configSpec, path, depth)
    if not result:
        return {}
    return result[0]


@router.get("/workspaces/{ws}/products/{ci_id}/decode-path/{p:path}")
def decode_path(ws: str, ci_id: str, p: str,
                current_user: Account = Depends(get_current_user),
                db: Session = Depends(get_db)):
    return svc.decode_path(db, ws, ci_id, p)


@router.get("/workspaces/{ws}/products/{ci_id}/baselines")
def list_baselines(ws: str, ci_id: str,
                   current_user: Account = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    return [{"id": b.id, "name": b.name, "type": b.type,
             "configurationItemId": b.configurationitem_id}
            for b in svc.list_baselines(db, ws, ci_id)]


@router.post("/workspaces/{ws}/products/{ci_id}/baselines", status_code=201)
@router.post("/workspaces/{ws}/products/{ci_id}/baselines/", status_code=201, include_in_schema=False)
def create_baseline(ws: str, ci_id: str, body: dict,
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    bl = svc.create_baseline(db, ws, ci_id, body.get("name", ""),
                              body.get("description", ""), body.get("type", 0),
                              current_user.login)
    return {"id": bl.id, "name": bl.name}


@router.delete("/workspaces/{ws}/products/{ci_id}/baselines/{bl_id}")
def delete_baseline(ws: str, ci_id: str, bl_id: int,
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    svc.delete_baseline(db, ws, bl_id)
    return {"status": "deleted"}


@router.get("/workspaces/{ws}/product-configurations")
def list_configs(ws: str, current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    return [{"id": c.id, "name": c.name} for c in svc.list_configs(db, ws)]


@router.post("/workspaces/{ws}/products/{ci_id}/configurations", status_code=201)
@router.post("/workspaces/{ws}/products/{ci_id}/configurations/", status_code=201, include_in_schema=False)
def create_config(ws: str, ci_id: str, body: dict,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    cfg = svc.create_config(db, ws, ci_id, body.get("name", ""),
                             body.get("description", ""), current_user.login)
    return {"id": cfg.id, "name": cfg.name}


@router.delete("/workspaces/{ws}/products/{ci_id}/configurations/{cfg_id}")
def delete_config(ws: str, ci_id: str, cfg_id: int,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    svc.delete_config(db, ws, cfg_id)
    return {"status": "deleted"}
