"""产品端点路由（ProductResource + Configurations + Baselines）。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.models.product import ProductConfiguration
from app.services.product_structure_service import ProductStructureService
from app.services.acl_helper import apply_acl

router = APIRouter()
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


def _config_to_dict(cfg, db) -> dict:
    """将 ProductConfiguration 转为前端需要的 JSON 结构。"""
    ws = cfg.configurationitem_workspace_id
    acl_data = None
    if cfg.acl_id and db:
        from app.models.security import ACL, AclUserEntry, AclUserGroupEntry
        acl = db.query(ACL).filter(ACL.id == cfg.acl_id).first()
        if acl:
            user_entries = db.query(AclUserEntry).filter(
                AclUserEntry.acl_id == cfg.acl_id).all()
            group_entries = db.query(AclUserGroupEntry).filter(
                AclUserGroupEntry.acl_id == cfg.acl_id).all()
            acl_data = {
                "userEntries": {
                    f"{e.principal_login}:{e.principal_workspace_id}": e.permission
                    for e in user_entries
                },
                "groupEntries": {
                    f"{e.principal_id}:{e.principal_workspace_id}": e.permission
                    for e in group_entries
                },
            }
    return {
        "id": cfg.id,
        "name": cfg.name,
        "configurationItemId": cfg.configurationitem_id,
        "description": cfg.description or "",
        "author": _get_user_dto(db, cfg.author_login, ws),
        "acl": acl_data,
        "creationDate": _fmt_date(cfg.creation_date),
        "substituteLinks": [],
        "optionalUsageLinks": [],
    }


# ── ProductBaselines（前端实际使用的路径：/product-baselines/{ci_id}/baselines）──

@router.get("/workspaces/{ws}/product-baselines")
def ci_scoped_baselines_root(ws: str,
                             current_user: Account = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    from app.models.product import ProductBaseline
    all_bl = db.query(ProductBaseline).filter(
        ProductBaseline.configurationitem_workspace_id == ws
    ).all()
    return [{"id": b.id, "name": b.name, "type": b.type,
             "configurationItemId": b.configurationitem_id}
            for b in all_bl]


@router.get("/workspaces/{ws}/product-baselines/{ci_id}/baselines")
def list_ci_baselines(ws: str, ci_id: str,
                      current_user: Account = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    return [{"id": b.id, "name": b.name, "type": b.type,
             "configurationItemId": b.configurationitem_id}
            for b in svc.list_baselines(db, ws, ci_id)]


@router.post("/workspaces/{ws}/product-baselines/{ci_id}/baselines", status_code=201)
@router.post("/workspaces/{ws}/product-baselines/{ci_id}/baselines/", status_code=201, include_in_schema=False)
def create_ci_scoped_baseline(ws: str, ci_id: str, body: dict,
                              current_user: Account = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    bl_type = body.get("type", 0)
    if isinstance(bl_type, str):
        bl_type = 0 if bl_type.upper() == "LATEST" else 1
    bl = svc.create_baseline(db, ws, ci_id, body.get("name", ""),
                               body.get("description", ""), bl_type,
                               current_user.login)
    return {"id": bl.id, "name": bl.name}


@router.get("/workspaces/{ws}/product-baselines/{ci_id}/baselines/{bl_id}")
def get_ci_baseline_detail(ws: str, ci_id: str, bl_id: int,
                           current_user: Account = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    from app.models.product import ProductBaseline
    bl = db.query(ProductBaseline).filter(ProductBaseline.id == bl_id).first()
    if not bl:
        from app.core.exceptions import EntityNotFoundException
        raise EntityNotFoundException("BaselineNotFoundException", str(bl_id))
    return {"id": bl.id, "name": bl.name, "type": bl.type,
            "configurationItemId": bl.configurationitem_id,
            "configurationItemWorkspaceId": bl.configurationitem_workspace_id,
            "creationDate": bl.creation_date.isoformat() + "Z" if bl.creation_date else None,
            "description": bl.description or "",
            "author": {"login": bl.author_login or "", "name": bl.author_login or ""},
            "baselinedParts": [], "substituteLinks": [], "optionalUsageLinks": [],
            "pathToPathLinks": []}


@router.delete("/workspaces/{ws}/product-baselines/{ci_id}/baselines/{bl_id}", status_code=204)
def delete_ci_baseline(ws: str, ci_id: str, bl_id: int,
                       current_user: Account = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    svc.delete_baseline(db, ws, bl_id)
    return {"status": "deleted"}


# ── Products（CI CRUD，保持向后兼容）──

@router.get("/workspaces/{ws}/products")
def list_cis(ws: str, current_user: Account = Depends(get_current_user),
             db: Session = Depends(get_db)):
    cis = svc.list_cis(db, ws)
    return [{"id": c.id, "workspaceId": c.workspace_id,
             "description": c.description,
             "designItemNumber": c.partmaster_partnumber,
             "designItemName": "",
             "designItemLatestVersion": "",
             "author": _get_user_dto(db, c.author_login, ws),
             "creationDate": _fmt_date(c.creation_date),
             "hasModificationNotification": False,
             "pathToPathLinks": []} for c in cis]


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
             "designItemNumber": ci.partmaster_partnumber,
             "designItemName": "",
             "designItemLatestVersion": "",
             "description": ci.description,
             "author": _get_user_dto(db, ci.author_login, ws),
             "creationDate": _fmt_date(ci.creation_date),
             "hasModificationNotification": False,
             "pathToPathLinks": []}


@router.get("/workspaces/{ws}/products/{ci_id}")
def get_ci(ws: str, ci_id: str,
           current_user: Account = Depends(get_current_user),
           db: Session = Depends(get_db)):
    ci = svc.get_ci(db, ws, ci_id)
    return {"id": ci.id, "workspaceId": ci.workspace_id,
             "description": ci.description,
             "designItemNumber": ci.partmaster_partnumber,
             "designItemName": "",
             "designItemLatestVersion": "",
             "author": _get_user_dto(db, ci.author_login, ws),
             "creationDate": _fmt_date(ci.creation_date),
             "hasModificationNotification": False,
             "pathToPathLinks": []}


@router.delete("/workspaces/{ws}/products/{ci_id}", status_code=204)
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
    return {"id": ci.id, "workspaceId": ci.workspace_id,
             "designItemNumber": ci.partmaster_partnumber,
             "designItemName": "",
             "designItemLatestVersion": "",
             "description": ci.description,
             "author": _get_user_dto(db, ci.author_login, ws),
             "creationDate": _fmt_date(ci.creation_date),
             "hasModificationNotification": False,
             "pathToPathLinks": []}


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


@router.get("/workspaces/{ws}/products/{ci_id}/baselines/{bl_id}")
def get_baseline(ws: str, ci_id: str, bl_id: int,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    from app.models.product import ProductBaseline
    bl = db.query(ProductBaseline).filter(ProductBaseline.id == bl_id).first()
    if not bl:
        from app.core.exceptions import EntityNotFoundException
        raise EntityNotFoundException("BaselineNotFoundException", str(bl_id))
    return {"id": bl.id, "name": bl.name, "type": bl.type,
            "configurationItemId": bl.configurationitem_id,
            "configurationItemWorkspaceId": bl.configurationitem_workspace_id,
            "creationDate": bl.creation_date.isoformat() + "Z" if bl.creation_date else None,
            "description": bl.description or "",
            "author": {"login": bl.author_login or "", "name": bl.author_login or ""},
            "baselinedParts": [], "substituteLinks": [], "optionalUsageLinks": [],
            "pathToPathLinks": []}


@router.post("/workspaces/{ws}/products/{ci_id}/baselines", status_code=201)
@router.post("/workspaces/{ws}/products/{ci_id}/baselines/", status_code=201, include_in_schema=False)
def create_baseline(ws: str, ci_id: str, body: dict,
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    bl_type = body.get("type", 0)
    if isinstance(bl_type, str):
        bl_type = 0 if bl_type.upper() == "LATEST" else 1
    bl = svc.create_baseline(db, ws, ci_id, body.get("name", ""),
                               body.get("description", ""), bl_type,
                               current_user.login)
    return {"id": bl.id, "name": bl.name}


@router.delete("/workspaces/{ws}/products/{ci_id}/baselines/{bl_id}")
def delete_baseline(ws: str, ci_id: str, bl_id: int,
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    svc.delete_baseline(db, ws, bl_id)
    return {"status": "deleted"}


@router.get("/workspaces/{ws}/product-baselines/{bl_id}")
def get_workspace_baseline(ws: str, bl_id: int,
                           current_user: Account = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    from app.models.product import ProductBaseline
    bl = db.query(ProductBaseline).filter(ProductBaseline.id == bl_id).first()
    if not bl:
        from app.core.exceptions import EntityNotFoundException
        raise EntityNotFoundException("BaselineNotFoundException", str(bl_id))
    return {"id": bl.id, "name": bl.name, "type": bl.type,
            "configurationItemId": bl.configurationitem_id,
            "creationDate": bl.creation_date.isoformat() + "Z" if bl.creation_date else None,
            "description": bl.description or ""}


@router.get("/workspaces/{ws}/product-baselines")
def list_all_baselines(ws: str,
                       current_user: Account = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    from app.models.product import ProductBaseline
    all_bl = db.query(ProductBaseline).filter(
        ProductBaseline.configurationitem_workspace_id == ws
    ).all()
    return [{"id": b.id, "name": b.name, "type": b.type,
             "configurationItemId": b.configurationitem_id}
            for b in all_bl]


@router.get("/workspaces/{ws}/product-configurations")
def list_configs(ws: str, current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    configs = svc.list_configs(db, ws)
    return [{"id": c.id, "name": c.name,
             "configurationItemId": c.configurationitem_id,
             "description": c.description or "",
             "author": _get_user_dto(db, c.author_login, ws),
             "acl": c.acl_id,
             "creationDate": _fmt_date(c.creation_date),
             "substituteLinks": [],
             "optionalUsageLinks": []}
            for c in configs]


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



# 前端使用的路径: /product-configurations/{ciId}/configurations/{id}
@router.get("/workspaces/{ws}/product-configurations/{ciId}/configurations/{cfg_id}")
@router.get("/workspaces/{ws}/product-configurations/{ciId}/configurations/{cfg_id}/", include_in_schema=False)
def get_config_by_ci(ws: str, ciId: str, cfg_id: int,
                     db: Session = Depends(get_db),
                     current_user: Account = Depends(get_current_user)):
    cfg = db.query(ProductConfiguration).filter(
        ProductConfiguration.id == cfg_id,
        ProductConfiguration.configurationitem_id == ciId,
        ProductConfiguration.configurationitem_workspace_id == ws,
    ).first()
    if not cfg:
        from app.core.exceptions import EntityNotFoundException
        raise EntityNotFoundException("ProductConfigurationNotFoundException", str(cfg_id))
    return _config_to_dict(cfg, db)


@router.delete("/workspaces/{ws}/product-configurations/{ciId}/configurations/{cfg_id}", status_code=204)
@router.delete("/workspaces/{ws}/product-configurations/{ciId}/configurations/{cfg_id}/", status_code=204, include_in_schema=False)
def delete_config_by_ci(ws: str, ciId: str, cfg_id: int,
                        db: Session = Depends(get_db),
                        current_user: Account = Depends(get_current_user)):
    cfg = db.query(ProductConfiguration).filter(
        ProductConfiguration.id == cfg_id,
        ProductConfiguration.configurationitem_id == ciId,
        ProductConfiguration.configurationitem_workspace_id == ws,
    ).first()
    if not cfg:
        from app.core.exceptions import EntityNotFoundException
        raise EntityNotFoundException("ProductConfigurationNotFoundException", str(cfg_id))
    svc.delete_config(db, ws, cfg_id)
    return Response(status_code=204)


@router.put("/workspaces/{ws}/products/{ci_id}/configurations/{cfg_id}/acl")
@router.put("/workspaces/{ws}/products/{ci_id}/configurations/{cfg_id}/acl/", include_in_schema=False)
def update_config_acl(ws: str, ci_id: str, cfg_id: int, body: dict,
                      db: Session = Depends(get_db),
                      current_user: Account = Depends(get_current_user)):
    config = db.query(ProductConfiguration).filter(
        ProductConfiguration.configurationitem_workspace_id == ws,
        ProductConfiguration.configurationitem_id == ci_id,
        ProductConfiguration.id == cfg_id,
    ).first()
    if not config:
        from app.core.exceptions import EntityNotFoundException
        raise EntityNotFoundException("ProductConfigurationNotFoundException", str(cfg_id))
    acl_id = getattr(config, "acl_id", None)
    new_acl_id = apply_acl(db, acl_id, body.get("userEntries", {}), body.get("groupEntries", {}))
    if config.acl_id != new_acl_id:
        config.acl_id = new_acl_id
        db.commit()
    return {"aclId": new_acl_id}


@router.get("/workspaces/{ws}/product-instances")
def list_product_instances(ws: str,
                            current_user: Account = Depends(get_current_user),
                            db: Session = Depends(get_db)):
    return []


@router.get("/workspaces/{ws}/products/{ci_id}/releases/last")
def last_release(ws: str, ci_id: str,
                  current_user: Account = Depends(get_current_user)):
    return []


@router.get("/workspaces/{ws}/products/{ci_id}/path-choices")
def path_choices(ws: str, ci_id: str,
                 type: str = Query(""),
                 current_user: Account = Depends(get_current_user)):
    return []


@router.get("/workspaces/{ws}/products/{ci_id}/versions-choices")
def versions_choices(ws: str, ci_id: str,
                      current_user: Account = Depends(get_current_user)):
    return []


@router.get("/workspaces/{ws}/products/{pid}/export-files")
def export_files(ws: str, pid: str,
                 current_user: Account = Depends(get_current_user)):
    return []


@router.get("/workspaces/{ws}/products/{pid}/path-to-path-links-types")
def path_to_path_links_types(ws: str, pid: str,
                              current_user: Account = Depends(get_current_user)):
    return []


@router.get("/workspaces/{ws}/products/{pid}/path-to-path-links/source/{source}/target/{target}")
def path_to_path_links_detail(ws: str, pid: str, source: str, target: str,
                               current_user: Account = Depends(get_current_user)):
    return {}


@router.get("/workspaces/{ws}/products/{pid}/layers")
def layers(ws: str, pid: str,
           current_user: Account = Depends(get_current_user)):
    return []


@router.get("/workspaces/{ws}/product-baselines/{pid}/baselines/{bid}/path-to-path-links-types")
def baseline_path_to_path_links_types(ws: str, pid: str, bid: int,
                                       current_user: Account = Depends(get_current_user)):
    return []


@router.get("/workspaces/{ws}/product-baselines/{pid}/baselines/{bid}/path-to-path-links/source/{source}/target/{target}")
def baseline_path_to_path_links_detail(ws: str, pid: str, bid: int,
                                        source: str, target: str,
                                        current_user: Account = Depends(get_current_user)):
    return {}


@router.get("/workspaces/{ws}/product-configurations/{pid}/configurations")
def list_ci_configs(ws: str, pid: str,
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    configs = svc.list_configs(db, ws, pid)
    return [{"id": c.id, "name": c.name,
             "configurationItemId": c.configurationitem_id,
             "description": c.description or "",
             "author": _get_user_dto(db, c.author_login, ws),
             "acl": c.acl_id,
             "creationDate": _fmt_date(c.creation_date),
             "substituteLinks": [],
             "optionalUsageLinks": []}
            for c in configs]


@router.get("/workspaces/{ws}/product-instances/{pid}/instances")
def list_ci_instances(ws: str, pid: str,
                       current_user: Account = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    instances = svc.list_instances(db, ws, pid)
    return [{"serialNumber": i.serialnumber,
             "workspaceId": i.workspace_id,
             "configurationItemId": i.configurationitem_id}
            for i in instances]


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
