"""产品端点路由（ConfigurationItem CRUD + 产品实例）。"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.models.product import ConfigurationItem, ProductInstanceMaster, ProductInstanceIteration
from app.models.part import PartMaster, PartRevision, PartIteration
from app.models.notification import ModificationNotification
from app.services.product_structure import ProductStructureService
from app.services.product_manager import ProductService
from app.schemas.product import ConfigurationItemDTO, ProductInstanceDTO

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

@router.get("/workspaces/{ws}/products", response_model=List[ConfigurationItemDTO])
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
    return [_ci_to_dict(db, c) for c in cis]


@router.post("/workspaces/{ws}/products", status_code=201, response_model=ConfigurationItemDTO)
@router.post("/workspaces/{ws}/products/", status_code=201, include_in_schema=False)
def create_ci(ws: str, body: dict,
              current_user: Account = Depends(get_current_user),
              db: Session = Depends(get_db)):
    ci_id = body.get("id", body.get("reference", ""))
    desc = body.get("description", "")
    part = body.get("designItemNumber", body.get("partNumber", body.get("partMasterNumber", "")))
    ci = svc.create_ci(db, ws, ci_id, desc, part, current_user.login)
    return _ci_to_dict(ci, db)


@router.get("/workspaces/{ws}/products/{ci_id}", response_model=ConfigurationItemDTO)
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


@router.put("/workspaces/{ws}/products/{ci_id}", response_model=ConfigurationItemDTO)
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


@router.get("/workspaces/{ws}/products/{ci_id}/bom")
@router.get("/workspaces/{ws}/products/{ci_id}/bom/", include_in_schema=False)
def bom(ws: str, ci_id: str,
        configSpec: str = Query("wip"), path: str = Query(None),
        diverge: bool = Query(False),
        current_user: Account = Depends(get_current_user),
        db: Session = Depends(get_db)):
    """BOM 端点，返回过滤后的 PartRevisionDTO 列表。"""
    result = svc.filter_product_structure(db, ws, ci_id, configSpec, path)
    if not result:
        return []
    # 平铺 ComponentDTO 树为 PartRevisionDTO 列表
    parts = []

    def flatten(comp, level=0):
        ci = svc.get_ci(db, ws, ci_id)
        rev = db.query(PartRevision).filter(
            PartRevision.workspace_id == ws,
            PartRevision.partmaster_partnumber == comp["number"],
        ).order_by(PartRevision.version.desc()).first()
        if rev is None:
            return
        last_it = rev.last_iteration
        acct = db.query(Account).filter(Account.login == rev.part_master.author_login).first()
        parts.append({
            "number": comp["number"],
            "version": comp["version"],
            "iteration": comp["iteration"],
            "name": comp["name"],
            "description": comp["description"],
            "checkOutUser": comp.get("checkOutUser"),
            "status": "RELEASED" if comp["released"] else ("OBSOLETE" if comp["obsolete"] else "WIP"),
            "author": comp["author"],
            "authorLogin": comp["authorLogin"],
            "checkOutDate": comp.get("checkOutDate"),
            "standardPart": comp["standardPart"],
            "assembly": comp["assembly"],
            "workspaceId": ws,
            "configurationItemId": ci_id,
        })
        for child in comp.get("components", []):
            flatten(child, level + 1)
    for comp in result:
        flatten(comp)
    return parts


# ── Product Instances ──

@router.get("/workspaces/{ws}/product-instances", response_model=List[ProductInstanceDTO])
@router.get("/workspaces/{ws}/product-instances/", include_in_schema=False)
def list_product_instances(ws: str,
                            current_user: Account = Depends(get_current_user),
                            db: Session = Depends(get_db)):
    instances = svc.list_instances(db, ws)
    return [{"serialNumber": i.serialnumber,
             "workspaceId": i.workspace_id,
             "configurationItemId": i.configurationitem_id}
            for i in instances]


@router.get("/workspaces/{ws}/product-instances/{sn}", response_model=ProductInstanceDTO)
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
    iterations = db.query(ProductInstanceIteration).filter(
        ProductInstanceIteration.workspace_id == ws,
        ProductInstanceIteration.prdinstancemaster_serialnumber == sn,
    ).order_by(ProductInstanceIteration.iteration).all()
    return {
        "serialNumber": inst.serialnumber,
        "workspaceId": inst.workspace_id,
        "configurationItemId": inst.configurationitem_id,
        "identifier": f"{ws}/{inst.configurationitem_id}-{inst.serialnumber}",
        "productInstanceIterations": [
            {
                "iteration": it.iteration,
                "iterationNote": it.iteration_note,
                "creationDate": _fmt_date(it.creation_date),
                "modificationDate": _fmt_date(it.modification_date),
                "author": _get_user_dto(db, it.author_login, ws),
                "productBaselineId": it.productbaseline_id,
            }
            for it in iterations
        ],
    }


@router.get("/workspaces/{ws}/product-instances/{pid}/instances", response_model=List[ProductInstanceDTO])
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
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """返回 CI 根零件的最新已发布版本。"""
    try:
        ci = svc.get_ci(db, ws, ci_id)
    except HTTPException:
        return []
    root_pn = ci.partmaster_partnumber
    rev = db.query(PartRevision).filter(
        PartRevision.workspace_id == ws,
        PartRevision.partmaster_partnumber == root_pn,
        PartRevision.status == 1,
    ).order_by(PartRevision.version.desc()).first()
    if rev is None:
        return []
    last_it = rev.last_iteration
    return [{
        "number": rev.partmaster_partnumber,
        "version": rev.version,
        "iteration": last_it.iteration if last_it else 1,
        "description": rev.description or "",
        "releaseDate": _fmt_date(rev.release_date),
    }]


@router.get("/workspaces/{ws}/products/{ci_id}/path-choices")
@router.get("/workspaces/{ws}/products/{ci_id}/path-choices/", include_in_schema=False)
def path_choices(ws: str, ci_id: str,
                 type: str = Query(""),
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    """返回 CI 下已存在的路径数据列表。CI 不存在则返回空列表。"""
    try:
        ci = svc.get_ci(db, ws, ci_id)
    except HTTPException:
        return []
    try:
        rows = db.execute(text(
            "SELECT DISTINCT pdm.path, pdm.id FROM pathdatamaster pdm "
            "JOIN prdinstiteration_pathdatamstr pipd ON pdm.id = pipd.pathdatamaster_id "
            "JOIN productinstanceiteration pii ON pii.workspace_id = pipd.workspace_id "
            "AND pii.configurationitem_id = pipd.configurationitem_id "
            "AND pii.prdinstancemaster_serialnumber = pipd.prdinstancemaster_serialnumber "
            "AND pii.iteration = pipd.iteration "
            "JOIN productinstancemaster pim ON pim.workspace_id = pii.workspace_id "
            "AND pim.configurationitem_id = pii.configurationitem_id "
            "AND pim.serialnumber = pii.prdinstancemaster_serialnumber "
            "WHERE pim.workspace_id = :ws AND pim.configurationitem_id = :ci"
        ), {"ws": ws, "ci": ci_id}).fetchall()
        return [{"id": r[1], "path": r[0]} for r in rows]
    except Exception:
        return []


@router.get("/workspaces/{ws}/products/{ci_id}/versions-choices")
@router.get("/workspaces/{ws}/products/{ci_id}/versions-choices/", include_in_schema=False)
def versions_choices(ws: str, ci_id: str,
                      current_user: Account = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    """返回 CI 根零件的所有版本列表。CI 不存在则返回空列表。"""
    try:
        ci = svc.get_ci(db, ws, ci_id)
    except HTTPException:
        return []
    root_pn = ci.partmaster_partnumber
    revs = db.query(PartRevision.version).filter(
        PartRevision.workspace_id == ws,
        PartRevision.partmaster_partnumber == root_pn,
    ).order_by(PartRevision.version).all()
    return [r[0] for r in revs]


@router.get("/workspaces/{ws}/products/{pid}/export-files")
@router.get("/workspaces/{ws}/products/{pid}/export-files/", include_in_schema=False)
def export_files(ws: str, pid: str,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    """返回 CI 的导出文件列表。暂未实现导出逻辑。"""
    return {"files": []}


@router.get("/workspaces/{ws}/products/{pid}/path-to-path-links-types")
@router.get("/workspaces/{ws}/products/{pid}/path-to-path-links-types/", include_in_schema=False)
def path_to_path_links_types(ws: str, pid: str,
                              current_user: Account = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    """返回 CI 的路径间链接类型列表。"""
    rows = db.execute(text(
        "SELECT id, type, name, sourcepath, targetpath, description "
        "FROM pathtopathlink "
        "WHERE workspace_id = :ws"
    ), {"ws": ws}).fetchall()
    return [{"id": r[0], "type": r[1], "name": r[2],
             "sourcePath": r[3], "targetPath": r[4], "description": r[5]}
            for r in rows]


@router.get("/workspaces/{ws}/products/{pid}/path-to-path-links/source/{source}/target/{target}")
@router.get("/workspaces/{ws}/products/{pid}/path-to-path-links/source/{source}/target/{target}/", include_in_schema=False)
def path_to_path_links_detail(ws: str, pid: str, source: str, target: str,
                               current_user: Account = Depends(get_current_user),
                               db: Session = Depends(get_db)):
    """返回指定源→目标的路径间链接详情。"""
    rows = db.execute(text(
        "SELECT id, type, name, description FROM pathtopathlink "
        "WHERE workspace_id = :ws AND sourcepath = :src AND targetpath = :tgt"
    ), {"ws": ws, "src": source, "tgt": target}).fetchall()
    return [{"id": r[0], "type": r[1], "name": r[2], "description": r[3]}
            for r in rows]


# ── Cascade ──

_part_svc = ProductService()


def _collect_ci_parts(db: Session, ws: str, ci_id: str) -> list[PartRevision]:
    """递归收集 CI 装配结构中的所有 PartRevision（去重）。CI 不存在时返回空列表。"""
    try:
        ci = svc.get_ci(db, ws, ci_id)
    except HTTPException:
        return []
    root_pn = ci.partmaster_partnumber
    master = db.query(PartMaster).filter(
        PartMaster.workspace_id == ws,
        PartMaster.number == root_pn,
    ).first()
    if not master or not master.revisions:
        return []
    seen: set[tuple] = set()
    collected: list[PartRevision] = []

    def collect(rev: PartRevision):
        key = (rev.workspace_id, rev.partmaster_partnumber, rev.version)
        if key in seen:
            return
        seen.add(key)
        collected.append(rev)
        last_it = rev.last_iteration
        if last_it:
            for link in (last_it.components or []):
                child = db.query(PartRevision).filter(
                    PartRevision.workspace_id == link.component_workspace_id,
                    PartRevision.partmaster_partnumber == link.component_partnumber,
                ).order_by(PartRevision.version.desc()).first()
                if child:
                    collect(child)

    collect(master.last_revision)
    return collected


@router.put("/workspaces/{ws}/products/{ci_id}/cascade-checkout")
@router.put("/workspaces/{ws}/products/{ci_id}/cascade-checkout/", include_in_schema=False)
def cascade_checkout(ws: str, ci_id: str,
                      current_user: Account = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    parts = _collect_ci_parts(db, ws, ci_id)
    checked_out = []
    errors = []
    for pr in parts:
        try:
            if not pr.checkout_user_login:
                _part_svc.checkout(db, ws, pr.partmaster_partnumber,
                                    pr.version, current_user.login)
                checked_out.append(pr.partmaster_partnumber)
        except Exception as e:
            errors.append({"part": pr.partmaster_partnumber + "-" + pr.version,
                           "error": str(e)})
    return {"status": "ok", "checkedOut": checked_out, "errors": errors}


@router.put("/workspaces/{ws}/products/{ci_id}/cascade-checkin")
@router.put("/workspaces/{ws}/products/{ci_id}/cascade-checkin/", include_in_schema=False)
def cascade_checkin(ws: str, ci_id: str,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    parts = _collect_ci_parts(db, ws, ci_id)
    checked_in = []
    errors = []
    for pr in parts:
        if pr.checkout_user_login != current_user.login:
            continue
        try:
            _part_svc.checkin(db, ws, pr.partmaster_partnumber,
                               pr.version, current_user.login)
            checked_in.append(pr.partmaster_partnumber)
        except Exception as e:
            errors.append({"part": pr.partmaster_partnumber + "-" + pr.version,
                           "error": str(e)})
    return {"status": "ok", "checkedIn": checked_in, "errors": errors}


@router.put("/workspaces/{ws}/products/{ci_id}/cascade-undocheckout")
@router.put("/workspaces/{ws}/products/{ci_id}/cascade-undocheckout/", include_in_schema=False)
def cascade_undocheckout(ws: str, ci_id: str,
                          current_user: Account = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    parts = _collect_ci_parts(db, ws, ci_id)
    undone = []
    errors = []
    for pr in parts:
        if pr.checkout_user_login != current_user.login:
            continue
        try:
            _part_svc.undo_checkout(db, ws, pr.partmaster_partnumber,
                                     pr.version, current_user.login)
            undone.append(pr.partmaster_partnumber)
        except Exception as e:
            errors.append({"part": pr.partmaster_partnumber + "-" + pr.version,
                           "error": str(e)})
    return {"status": "ok", "undoneCheckout": undone, "errors": errors}
