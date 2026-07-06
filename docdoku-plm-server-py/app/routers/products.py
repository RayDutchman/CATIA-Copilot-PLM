"""产品端点路由（ConfigurationItem CRUD + 产品实例）。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.models.product import ConfigurationItem, ProductInstanceMaster
from app.models.part import PartMaster, PartRevision
from app.models.notification import ModificationNotification
from app.services.product_structure import ProductStructureService

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
svc = ProductStructureService()

_NAME_CACHE: dict = {}


def _get_user_dto(db: Session, login: str, ws: str) -> dict:
    if not login:
        return {"login": "", "name": "", "email": None, "language": None, "workspaceId": ws}
    if login in _NAME_CACHE:
        cached = _NAME_CACHE[login]
        return {"login": login, "name": cached, "email": None, "language": None, "workspaceId": ws}
    from app.models.auth import Account
    acc = db.query(Account).filter(Account.login == login).first()
    name = acc.name if (acc and acc.name) else login
    _NAME_CACHE[login] = name
    return {"login": login, "name": name, "email": None, "language": None, "workspaceId": ws}


def _fmt_date(d) -> str | None:
    if d is None:
        return None
    return d.strftime("%Y-%m-%dT%H:%M:%S.") + f"{d.microsecond // 1000:03d}Z"


def _ci_to_dict(ci: ConfigurationItem, db: Session) -> dict:
    name = ""
    latest_version = ""
    if ci.partmaster_partnumber:
        master = db.query(PartMaster).filter(
            PartMaster.workspace_id == ci.workspace_id,
            PartMaster.number == ci.partmaster_partnumber,
        ).first()
        if master:
            name = master.name or ""
        rev = db.query(PartRevision).filter(
            PartRevision.workspace_id == ci.workspace_id,
            PartRevision.partmaster_partnumber == ci.partmaster_partnumber,
        ).order_by(PartRevision.creation_date.desc()).first()
        if rev:
            latest_version = rev.version
    return {
        "id": ci.id, "workspaceId": ci.workspace_id,
        "description": ci.description,
        "designItemNumber": ci.partmaster_partnumber,
        "designItemName": name,
        "designItemLatestVersion": latest_version,
        "author": _get_user_dto(db, ci.author_login, ci.workspace_id),
        "creationDate": _fmt_date(ci.creation_date),
        "hasModificationNotification": (
            db.query(ModificationNotification).filter(
                ModificationNotification.impacted_workspace_id == ci.workspace_id,
                ModificationNotification.impacted_partmaster_partnumber == ci.partmaster_partnumber,
            ).count() > 0
        ),
        "pathToPathLinks": [],
    }


# ── Products（CI CRUD）──

@router.get("/workspaces/{ws}/products")
@router.get("/workspaces/{ws}/products/", include_in_schema=False)
def list_cis(ws: str, current_user: Account = Depends(get_current_user),
             db: Session = Depends(get_db)):
    cis = svc.list_cis(db, ws)
    return [_ci_to_dict(c, db) for c in cis]


@router.get("/workspaces/{ws}/products/numbers")
@router.get("/workspaces/{ws}/products/numbers/", include_in_schema=False)
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
    return _ci_to_dict(ci, db)


@router.get("/workspaces/{ws}/products/{ci_id}")
@router.get("/workspaces/{ws}/products/{ci_id}/", include_in_schema=False)
def get_ci(ws: str, ci_id: str,
           current_user: Account = Depends(get_current_user),
           db: Session = Depends(get_db)):
    ci = svc.get_ci(db, ws, ci_id)
    return _ci_to_dict(ci, db)


@router.delete("/workspaces/{ws}/products/{ci_id}", status_code=204)
@router.delete("/workspaces/{ws}/products/{ci_id}/", status_code=204, include_in_schema=False)
def delete_ci(ws: str, ci_id: str,
              current_user: Account = Depends(get_current_user),
              db: Session = Depends(get_db)):
    svc.delete_ci(db, ws, ci_id)
    return Response(status_code=204)


@router.put("/workspaces/{ws}/products/{ci_id}")
@router.put("/workspaces/{ws}/products/{ci_id}/", include_in_schema=False)
def update_ci(ws: str, ci_id: str, body: dict,
              current_user: Account = Depends(get_current_user),
              db: Session = Depends(get_db)):
    ci = svc.update_ci(db, ws, ci_id, body)
    return _ci_to_dict(ci, db)


@router.get("/workspaces/{ws}/products/{ci_id}/filter")
@router.get("/workspaces/{ws}/products/{ci_id}/filter/", include_in_schema=False)
def filter_structure(ws: str, ci_id: str,
                     configSpec: str = Query(None), path: str = Query(None),
                     depth: int = Query(None),
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    result = svc.filter_product_structure(db, ws, ci_id, configSpec, path, depth)
    if not result:
        return {}
    return result[0]


@router.get("/workspaces/{ws}/products/{ci_id}/decode-path/{p:path}")
@router.get("/workspaces/{ws}/products/{ci_id}/decode-path/{p:path}/", include_in_schema=False)
def decode_path(ws: str, ci_id: str, p: str,
                current_user: Account = Depends(get_current_user),
                db: Session = Depends(get_db)):
    return svc.decode_path(db, ws, ci_id, p)


# ── Product Instances ──

@router.get("/workspaces/{ws}/product-instances")
@router.get("/workspaces/{ws}/product-instances/", include_in_schema=False)
def list_product_instances(ws: str,
                            current_user: Account = Depends(get_current_user),
                            db: Session = Depends(get_db)):
    instances = svc.list_instances(db, ws)
    return [{"serialNumber": i.serialnumber,
             "workspaceId": i.workspace_id,
             "configurationItemId": i.configurationitem_id}
            for i in instances]


@router.get("/workspaces/{ws}/product-instances/{sn}")
@router.get("/workspaces/{ws}/product-instances/{sn}/", include_in_schema=False)
def get_product_instance(ws: str, sn: str,
                          current_user: Account = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    inst = db.query(ProductInstanceMaster).filter(
        ProductInstanceMaster.workspace_id == ws,
        ProductInstanceMaster.serialnumber == sn,
    ).first()
    if not inst:
        raise HTTPException(404, "Product instance not found")
    return {"serialNumber": inst.serialnumber,
            "workspaceId": inst.workspace_id,
            "configurationItemId": inst.configurationitem_id}


@router.get("/workspaces/{ws}/product-instances/{pid}/instances")
@router.get("/workspaces/{ws}/product-instances/{pid}/instances/", include_in_schema=False)
def list_ci_instances(ws: str, pid: str,
                       current_user: Account = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    instances = svc.list_instances(db, ws, pid)
    return [{"serialNumber": i.serialnumber,
             "workspaceId": i.workspace_id,
             "configurationItemId": i.configurationitem_id}
            for i in instances]


# ── Stubs ──

@router.get("/workspaces/{ws}/products/{ci_id}/releases/last")
@router.get("/workspaces/{ws}/products/{ci_id}/releases/last/", include_in_schema=False)
def last_release(ws: str, ci_id: str,
                  current_user: Account = Depends(get_current_user)):
    return []


@router.get("/workspaces/{ws}/products/{ci_id}/path-choices")
@router.get("/workspaces/{ws}/products/{ci_id}/path-choices/", include_in_schema=False)
def path_choices(ws: str, ci_id: str,
                 type: str = Query(""),
                 current_user: Account = Depends(get_current_user)):
    return []


@router.get("/workspaces/{ws}/products/{ci_id}/versions-choices")
@router.get("/workspaces/{ws}/products/{ci_id}/versions-choices/", include_in_schema=False)
def versions_choices(ws: str, ci_id: str,
                      current_user: Account = Depends(get_current_user)):
    return []


@router.get("/workspaces/{ws}/products/{pid}/export-files")
@router.get("/workspaces/{ws}/products/{pid}/export-files/", include_in_schema=False)
def export_files(ws: str, pid: str,
                 current_user: Account = Depends(get_current_user)):
    return []


@router.get("/workspaces/{ws}/products/{pid}/path-to-path-links-types")
@router.get("/workspaces/{ws}/products/{pid}/path-to-path-links-types/", include_in_schema=False)
def path_to_path_links_types(ws: str, pid: str,
                              current_user: Account = Depends(get_current_user)):
    return []


@router.get("/workspaces/{ws}/products/{pid}/path-to-path-links/source/{source}/target/{target}")
@router.get("/workspaces/{ws}/products/{pid}/path-to-path-links/source/{source}/target/{target}/", include_in_schema=False)
def path_to_path_links_detail(ws: str, pid: str, source: str, target: str,
                               current_user: Account = Depends(get_current_user)):
    return {}


# ── Cascade ──

@router.put("/workspaces/{ws}/products/{ci_id}/cascade-checkout")
@router.put("/workspaces/{ws}/products/{ci_id}/cascade-checkout/", include_in_schema=False)
def cascade_checkout(ws: str, ci_id: str,
                      current_user: Account = Depends(get_current_user)):
    return {"status": "ok"}


@router.put("/workspaces/{ws}/products/{ci_id}/cascade-checkin")
@router.put("/workspaces/{ws}/products/{ci_id}/cascade-checkin/", include_in_schema=False)
def cascade_checkin(ws: str, ci_id: str,
                     current_user: Account = Depends(get_current_user)):
    return {"status": "ok"}


@router.put("/workspaces/{ws}/products/{ci_id}/cascade-undocheckout")
@router.put("/workspaces/{ws}/products/{ci_id}/cascade-undocheckout/", include_in_schema=False)
def cascade_undocheckout(ws: str, ci_id: str,
                          current_user: Account = Depends(get_current_user)):
    return {"status": "ok"}
