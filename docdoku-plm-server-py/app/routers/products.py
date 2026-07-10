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


def _p2p_svc_lazy(db, ws: str, ci_id: str) -> list:
    """延迟查询 CI 的 PathToPathLink 列表（避免在文件顶部循环引用）。"""
    from app.services.products.path_to_path_service import path_to_path_service
    try:
        return path_to_path_service.get_links_for_ci(db, ws, ci_id)
    except Exception:
        return []


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
        "hasModificationNotification": svc._has_modification_notification(
            db, ci.workspace_id, ci.partmaster_partnumber
        ) if ci.partmaster_partnumber else False,
        "pathToPathLinks": _p2p_svc_lazy(db, ci.workspace_id, ci.id),
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
    from app.services.factory.acl_factory import check_read_access
    is_admin = db.execute(text(
        "SELECT 1 FROM usergroupmapping WHERE login=:l AND groupname='admin'"
    ), {"l": current_user.login}).first() is not None
    result = svc.filter_product_structure(db, ws, ci_id, configSpec, path, depth,
                                           user_login=current_user.login,
                                           is_admin=is_admin)
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
    is_admin = db.execute(text(
        "SELECT 1 FROM usergroupmapping WHERE login=:l AND groupname='admin'"
    ), {"l": current_user.login}).first() is not None
    result = svc.filter_product_structure(db, ws, ci_id, configSpec, path,
                                           user_login=current_user.login,
                                           is_admin=is_admin)
    if not result:
        return []
    # 平铺 ComponentDTO 树为 PartRevisionDTO 列表
    parts = []

    def flatten(comp, level=0):
        parts.append({
            "partKey": f"{comp['number']}-{comp['version']}",
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
            "notifications": comp.get("notifications", []),
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
        "configurationItemId": inst.configurationitem_id,
        "identifier": f"{ws}/{inst.configurationitem_id}-{inst.serialnumber}",
        "productInstanceIterations": [
            {
                "iteration": it.iteration,
                "iterationNote": it.iteration_note,
                "creationDate": _fmt_date(it.creation_date),
                "modificationDate": _fmt_date(it.modification_date),
                "author": _get_user_dto(db, it.author_login, ws),
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
    author_name = rev.part_master.author_login or ""
    pm_author = db.query(Account).filter(Account.login == rev.part_master.author_login).first()
    if pm_author and pm_author.name:
        author_name = pm_author.name
    chk_user = None
    if rev.checkout_user_login:
        chk_acct = db.query(Account).filter(Account.login == rev.checkout_user_login).first()
        chk_user = {
            "login": rev.checkout_user_login,
            "name": (chk_acct.name if chk_acct and chk_acct.name else rev.checkout_user_login) or "",
            "email": chk_acct.email if chk_acct else None,
            "language": chk_acct.language if chk_acct else None,
            "workspaceId": rev.checkout_user_workspace_id or ws,
        }
    return {
        "partKey": f"{rev.partmaster_partnumber}-{rev.version}",
        "number": rev.partmaster_partnumber,
        "version": rev.version,
        "name": rev.part_master.name or "",
        "iteration": last_it.iteration if last_it else 1,
        "description": rev.description or "",
        "author": author_name,
        "authorLogin": rev.part_master.author_login or "",
        "checkOutUser": chk_user,
        "checkOutDate": _fmt_date(rev.check_out_date),
        "releaseDate": _fmt_date(rev.release_date),
        "standardPart": rev.part_master.standard_part or False,
        "assembly": bool(last_it and last_it.components),
        "workspaceId": ws,
        "configurationItemId": ci_id,
    }


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
    # PathDataMasterNotFoundException: 等待 PathData 域实现后抛出
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
    revs = db.query(PartRevision).filter(
        PartRevision.workspace_id == ws,
        PartRevision.partmaster_partnumber == root_pn,
    ).order_by(PartRevision.version).all()
    result = []
    for rev in revs:
        last_it = rev.last_iteration
        result.append({
            "partNumber": rev.partmaster_partnumber,
            "version": rev.version,
            "iteration": last_it.iteration if last_it else 1,
            "name": rev.part_master.name or "",
        })
    return result


@router.get("/workspaces/{ws}/products/{pid}/export-files")
@router.get("/workspaces/{ws}/products/{pid}/export-files/", include_in_schema=False)
def export_files(ws: str, pid: str,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    """以 ZIP 格式下载 CI 下所有零件的 CAD 文件（nativeCAD + 附件）。

    对齐 Java ProductFileExportMessageBodyWriter。
    """
    from app.routers.export.product_file_export import build_product_export_zip
    from fastapi.responses import StreamingResponse

    zip_data = build_product_export_zip(db, ws, pid)
    return StreamingResponse(
        iter([zip_data]),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{pid}-export.zip"',
            "Content-Length": str(len(zip_data)),
        },
    )


@router.get("/workspaces/{ws}/products/{pid}/path-to-path-links-types")
@router.get("/workspaces/{ws}/products/{pid}/path-to-path-links-types/", include_in_schema=False)
def path_to_path_links_types(ws: str, pid: str,
                              current_user: Account = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    """返回 CI 下所有路径间链接的去重类型列表。

    对齐 Payara ProductManagerBean.getPathToPathLinkTypes()：
    通过 configurationitem_p2plink 关联表找属于该 CI 的 links，再去重 type。
    """
    rows = db.execute(text(
        "SELECT DISTINCT ppl.type "
        "FROM pathtopathlink ppl "
        "JOIN configurationitem_p2plink cp ON cp.pathtopathlink_id = ppl.id "
        "WHERE cp.workspace_id = :ws AND cp.configurationitem_id = :ci"
    ), {"ws": ws, "ci": pid}).fetchall()
    return [r[0] for r in rows if r[0]]


@router.get("/workspaces/{ws}/products/{pid}/path-to-path-links/source/{source:path}/target/{target:path}")
@router.get("/workspaces/{ws}/products/{pid}/path-to-path-links/source/{source:path}/target/{target:path}/", include_in_schema=False)
def path_to_path_links_detail(ws: str, pid: str, source: str, target: str,
                               current_user: Account = Depends(get_current_user),
                               db: Session = Depends(get_db)):
    """返回 CI 下指定源→目标路径的链接列表。

    对齐 Payara ProductManagerBean.getPathToPathLinkFromSourceAndTarget()。
    """
    rows = db.execute(text(
        "SELECT ppl.id, ppl.type, ppl.description, ppl.sourcepath, ppl.targetpath "
        "FROM pathtopathlink ppl "
        "JOIN configurationitem_p2plink cp ON cp.pathtopathlink_id = ppl.id "
        "WHERE cp.workspace_id = :ws AND cp.configurationitem_id = :ci "
        "AND ppl.sourcepath = :src AND ppl.targetpath = :tgt"
    ), {"ws": ws, "ci": pid, "src": source, "tgt": target}).fetchall()
    return [{"id": r[0], "type": r[1], "description": r[2],
             "sourceComponents": [], "targetComponents": []}
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


# ── Stub endpoints ──
# PathToPathCyclicException: 等待 PathData 域实现后抛出（path-to-path link 环检测）
# PathToPathLinkAlreadyExistsException: 等待 PathData 域实现后抛出（重复 link）
# PathToPathLinkNotFoundException: 等待 PathData 域实现后抛出（link 不存在）

@router.get("/workspaces/{ws}/products/{ci_id}/paths")
@router.get("/workspaces/{ws}/products/{ci_id}/paths/", include_in_schema=False)
def ci_paths(ws: str, ci_id: str,
             search: str = Query(None),
             current_user: Account = Depends(get_current_user),
             db: Session = Depends(get_db)):
    return []


@router.get("/workspaces/{ws}/products/{ci_id}/document-links/{pn}-{pv}-{pi}/{config_spec}")
@router.get("/workspaces/{ws}/products/{ci_id}/document-links/{pn}-{pv}-{pi}/{config_spec}/", include_in_schema=False)
def ci_document_links(ws: str, ci_id: str,
                       pn: str, pv: str, pi: int, config_spec: str,
                       current_user: Account = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    return []


@router.get("/workspaces/{ws}/products/{ci_id}/document-links/{pn}/{config_spec}")
@router.get("/workspaces/{ws}/products/{ci_id}/document-links/{pn}/{config_spec}/", include_in_schema=False)
def ci_document_links_wip(ws: str, ci_id: str, pn: str, config_spec: str,
                           current_user: Account = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    """返回 CI 下指定零件的最新 document-links（WIP 配置规约）。"""
    from app.models.product import PartRevision, PartIteration
    from app.models.document import DocumentLink

    rev = db.query(PartRevision).filter(
        PartRevision.workspace_id == ws,
        PartRevision.partmaster_partnumber == pn,
    ).order_by(PartRevision.creation_date.desc()).first()
    if not rev:
        return []
    last_it = rev.last_iteration
    if not last_it:
        return []
    links = db.query(DocumentLink).filter(
        DocumentLink.workspace_id == ws,
        DocumentLink.partmaster_partnumber == last_it.partmaster_partnumber,
        DocumentLink.partrevision_version == last_it.partrevision_version,
        DocumentLink.iteration == last_it.iteration,
    ).all()
    result = []
    for dl in links:
        result.append({
            "documentMasterId": dl.targetdocumentmaster_id,
            "documentRevisionVersion": dl.targetdocumentrevision_version,
            "iteration": dl.target_iteration,
            "workspaceId": ws,
            "commentLink": dl.comment or "",
        })
    return result


# ══════════════════════════════════════════════════════════
# CI 级 PathToPathLink CRUD（对齐 Payara ProductManagerBean）
# ══════════════════════════════════════════════════════════

from app.services.products.path_to_path_service import path_to_path_service as _p2p_svc


@router.get("/workspaces/{ws}/products/{ci_id}/path-to-path-links")
@router.get("/workspaces/{ws}/products/{ci_id}/path-to-path-links/", include_in_schema=False)
def ci_p2p_links_list(ws: str, ci_id: str,
                       current_user: Account = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """获取 CI 的所有 PathToPathLink 列表。"""
    return _p2p_svc.get_links_for_ci(db, ws, ci_id)


@router.post("/workspaces/{ws}/products/{ci_id}/path-to-path-links", status_code=201)
@router.post("/workspaces/{ws}/products/{ci_id}/path-to-path-links/", status_code=201, include_in_schema=False)
def ci_create_p2p_link(ws: str, ci_id: str, body: dict,
                        current_user: Account = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    """创建 CI 级 PathToPathLink（含环检测）。"""
    link_type = body.get("type", "")
    path_from = body.get("sourcePath", body.get("pathFrom", ""))
    path_to = body.get("targetPath", body.get("pathTo", ""))
    description = body.get("description", "")
    return _p2p_svc.create_path_to_path_link(
        db, ws, ci_id, link_type, path_from, path_to, description
    )


@router.get("/workspaces/{ws}/products/{ci_id}/path-to-path-links/{link_id}")
@router.get("/workspaces/{ws}/products/{ci_id}/path-to-path-links/{link_id}/", include_in_schema=False)
def ci_p2p_link_by_id(ws: str, ci_id: str, link_id: int,
                       current_user: Account = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """按 ID 获取 CI 级单个 PathToPathLink。"""
    from app.core.exceptions import PathToPathLinkNotFoundException
    link = _p2p_svc.get_link_by_id(db, link_id)
    if not link:
        raise PathToPathLinkNotFoundException("PathToPathLinkNotFoundException", str(link_id))
    return link


@router.put("/workspaces/{ws}/products/{ci_id}/path-to-path-links/{link_id}")
@router.put("/workspaces/{ws}/products/{ci_id}/path-to-path-links/{link_id}/", include_in_schema=False)
def ci_update_p2p_link(ws: str, ci_id: str, link_id: int, body: dict,
                        current_user: Account = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    """更新 CI 级 PathToPathLink（只能改 description）。"""
    description = body.get("description", "")
    return _p2p_svc.update_path_to_path_link(db, ws, ci_id, link_id, description)


@router.delete("/workspaces/{ws}/products/{ci_id}/path-to-path-links/{link_id}", status_code=204)
@router.delete("/workspaces/{ws}/products/{ci_id}/path-to-path-links/{link_id}/", status_code=204, include_in_schema=False)
def ci_delete_p2p_link(ws: str, ci_id: str, link_id: int,
                        current_user: Account = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    """删除 CI 级 PathToPathLink。"""
    from fastapi.responses import Response
    _p2p_svc.delete_path_to_path_link(db, ws, ci_id, link_id)
    return Response(status_code=204)
