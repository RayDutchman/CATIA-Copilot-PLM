"""产品端点路由（ConfigurationItem CRUD + 产品实例）。"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models.util.date_utils import format_iso_date
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


def _p2p_svc_lazy(db, ws: str, ci_id: str) -> list:
    """延迟查询 CI 的 PathToPathLink 列表（避免在文件顶部循环引用）。"""
    from app.services.products.path_to_path_service import path_to_path_service
    try:
        return path_to_path_service.get_links_for_ci(db, ws, ci_id)
    except Exception:
        return []


def _build_instance_master_dict(db: Session, inst: ProductInstanceMaster) -> dict:
    """构建完整 ProductInstanceMasterDTO（identifier + acl + iteration 列表）。

    对齐 Java ProductInstanceMasterDTO（serialNumber/configurationItemId/identifier/
    productInstanceIterations/acl）。P2-07：list_product_instances / list_ci_instances
    复用此函数输出完整 DTO。
    """
    ws = inst.workspace_id
    sn = inst.serialnumber
    ci_id = inst.configurationitem_id

    # ── acl ──
    from app.models.security import ACL, AclUserEntry, AclUserGroupEntry
    acl_data = None
    if inst.acl_id:
        acl = db.query(ACL).filter(ACL.id == inst.acl_id).first()
        if acl:
            user_entries = db.query(AclUserEntry).filter(AclUserEntry.acl_id == inst.acl_id).all()
            group_entries = db.query(AclUserGroupEntry).filter(AclUserGroupEntry.acl_id == inst.acl_id).all()
            _PERM = {0: "FORBIDDEN", 1: "READ_ONLY", 2: "FULL_ACCESS"}
            acl_data = {
                "userEntries": [
                    {"key": e.principal_login, "value": _PERM.get(e.permission, "FORBIDDEN")}
                    for e in user_entries
                ],
                "groupEntries": [
                    {"key": e.principal_id, "value": _PERM.get(e.permission, "FORBIDDEN")}
                    for e in group_entries
                ],
                "userEntriesMap": {e.principal_login: _PERM.get(e.permission, "FORBIDDEN") for e in user_entries},
                "userGroupEntriesMap": {e.principal_id: _PERM.get(e.permission, "FORBIDDEN") for e in group_entries},
            }

    # ── iterations ──
    iterations = db.query(ProductInstanceIteration).filter(
        ProductInstanceIteration.workspace_id == ws,
        ProductInstanceIteration.prdinstancemaster_serialnumber == sn,
    ).order_by(ProductInstanceIteration.iteration).all()

    from app.services.products.path_to_path_service import path_to_path_service
    from app.models.configuration.product_baseline import ProductBaseline

    iterations_list = []
    for it in iterations:
        it_num = it.iteration
        # substituteLinks / optionalUsageLinks / substitutesParts / optionalsParts
        # pathDataMasterList / pathDataPaths / pathToPathLinks / basedOn
        # instanceAttributes / linkedDocuments / attachedFiles
        # （与 get_product_instance 中逐 iteration 填充逻辑一致）
        sub_rows = db.execute(text(
            "SELECT substitutelinks FROM prdinstanceiteration_sublink "
            "WHERE workspace_id=:ws AND configurationitem_id=:ci "
            "AND prdinstancemaster_serialnumber=:sn AND iteration=:it"
        ), {"ws": ws, "ci": ci_id, "sn": sn, "it": it_num}).fetchall()
        substitute_links = [r[0] for r in sub_rows if r[0]]

        opt_rows = db.execute(text(
            "SELECT optionalusagelinks FROM prdinstanceiteration_optlink "
            "WHERE workspace_id=:ws AND configurationitem_id=:ci "
            "AND prdinstancemaster_serialnumber=:sn AND iteration=:it"
        ), {"ws": ws, "ci": ci_id, "sn": sn, "it": it_num}).fetchall()
        optional_links = [r[0] for r in opt_rows if r[0]]

        substitutes_parts = []
        for path_str in substitute_links:
            try:
                decoded = svc.decode_path(db, ws, ci_id, path_str)
                if decoded:
                    substitutes_parts.append({"partLinks": decoded})
            except Exception:
                pass

        optionals_parts = []
        for path_str in optional_links:
            try:
                decoded = svc.decode_path(db, ws, ci_id, path_str)
                if decoded:
                    optionals_parts.append({"partLinks": decoded})
            except Exception:
                pass

        pdm_rows = db.execute(text(
            "SELECT pdm.id, pdm.path FROM pathdatamaster pdm "
            "JOIN prdinstiteration_pathdatamstr pipd ON pipd.pathdatamaster_id = pdm.id "
            "WHERE pipd.workspace_id=:ws AND pipd.configurationitem_id=:ci "
            "AND pipd.prdinstancemaster_serialnumber=:sn "
            "AND pipd.prdinstanceiteration_iteration=:it"
        ), {"ws": ws, "ci": ci_id, "sn": sn, "it": it_num}).fetchall()
        path_data_masters = [{"id": r[0], "path": r[1]} for r in pdm_rows]

        path_data_paths = []
        for pdm in path_data_masters:
            try:
                decoded = svc.decode_path(db, ws, ci_id, pdm["path"])
                if decoded:
                    path_data_paths.append({"partLinks": decoded})
            except Exception:
                pass

        p2p_rows = db.execute(text(
            "SELECT ppl.id, ppl.type, ppl.description, ppl.sourcepath, ppl.targetpath "
            "FROM pathtopathlink ppl "
            "JOIN prdinstiteration_p2plink pip ON pip.pathtopathlink_id = ppl.id "
            "WHERE pip.workspace_id=:ws AND pip.configurationitem_id=:ci "
            "AND pip.prdinstancemaster_serialnumber=:sn AND pip.iteration=:it"
        ), {"ws": ws, "ci": ci_id, "sn": sn, "it": it_num}).fetchall()
        path_to_path_links = [
            path_to_path_service._link_row_to_dict(r, db=db, ws=ws, ci_id=ci_id)
            for r in p2p_rows
        ]

        based_on = None
        if it.productbaseline_id:
            baseline = db.query(ProductBaseline).filter(
                ProductBaseline.id == it.productbaseline_id,
            ).first()
            if baseline:
                based_on = {
                    "id": baseline.id,
                    "name": baseline.name,
                    "description": baseline.description,
                }

        attr_rows = db.execute(text(
            "SELECT ia.id, ia.name, ia.mandatory, ia.locked, ia.booleanvalue, "
            "ia.datevalue, ia.indexvalue, ia.numbervalue, ia.textvalue, "
            "ia.longtextvalue, ia.urlvalue "
            "FROM instanceattribute ia "
            "JOIN prdinstiteration_attribute pia ON pia.instanceattribute_id = ia.id "
            "WHERE pia.workspace_id=:ws AND pia.configurationitem_id=:ci "
            "AND pia.prdinstancemaster_serialnumber=:sn AND pia.iteration=:it "
            "ORDER BY pia.attribute_order"
        ), {"ws": ws, "ci": ci_id, "sn": sn, "it": it_num}).fetchall()
        instance_attrs = [{
            "id": r[0], "name": r[1], "mandatory": r[2], "locked": r[3],
            "booleanValue": r[4],
            "dateValue": str(r[5]) if r[5] else None,
            "indexValue": r[6], "numberValue": r[7],
            "textValue": r[8], "longTextValue": r[9], "urlValue": r[10],
        } for r in attr_rows]

        doc_rows = db.execute(text(
            "SELECT dl.id, dl.target_documentmaster_id, dl.target_docrevision_version, "
            "dl.target_workspace_id, dl.commentdata "
            "FROM documentlink dl "
            "JOIN prdinstiteration_documentlink pid ON pid.documentlink_id = dl.id "
            "WHERE pid.workspace_id=:ws AND pid.configurationitem_id=:ci "
            "AND pid.prdinstancemaster_serialnumber=:sn AND pid.iteration=:it"
        ), {"ws": ws, "ci": ci_id, "sn": sn, "it": it_num}).fetchall()
        linked_docs = [{
            "id": r[0], "documentMasterId": r[1], "version": r[2],
            "workspaceId": r[3], "commentLink": r[4] or "",
        } for r in doc_rows]

        file_rows = db.execute(text(
            "SELECT br.fullname, br.dtype, br.contentlength, br.lastmodified, "
            "br.quality, br.x_max, br.x_min, br.y_max, br.y_min, br.z_max, br.z_min "
            "FROM binaryresource br "
            "JOIN prdinstiteration_binres pib ON pib.attachedfile_fullname = br.fullname "
            "WHERE pib.workspace_id=:ws AND pib.configurationitem_id=:ci "
            "AND pib.prdinstancemaster_serialnumber=:sn AND pib.iteration=:it"
        ), {"ws": ws, "ci": ci_id, "sn": sn, "it": it_num}).fetchall()
        attached_files = [{
            "fullName": r[0], "type": r[1], "contentLength": r[2],
            "lastModified": str(r[3]) if r[3] else None,
            "quality": r[4], "xMax": r[5], "xMin": r[6],
            "yMax": r[7], "yMin": r[8], "zMax": r[9], "zMin": r[10],
        } for r in file_rows]

        iterations_list.append({
            "iteration": it_num,
            "iterationNote": it.iteration_note,
            "creationDate": format_iso_date(it.creation_date),
            "modificationDate": format_iso_date(it.modification_date),
            "author": _get_user_dto(db, it.author_login, ws),
            "substituteLinks": substitute_links,
            "optionalUsageLinks": optional_links,
            "substitutesParts": substitutes_parts,
            "optionalsParts": optionals_parts,
            "pathDataMasterList": path_data_masters,
            "pathDataPaths": path_data_paths,
            "pathToPathLinks": path_to_path_links,
            "basedOn": based_on,
            "instanceAttributes": instance_attrs,
            "linkedDocuments": linked_docs,
            "attachedFiles": attached_files,
        })

    return {
        "serialNumber": sn,
        "configurationItemId": ci_id,
        "identifier": f"{ws}/{ci_id}-{sn}",
        "acl": acl_data,
        "productInstanceIterations": iterations_list,
    }


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
        "creationDate": format_iso_date(ci.creation_date),
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
    return [_ci_to_dict(c, db) for c in cis]


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
                     linkType: Optional[str] = Query(None),
                     diverge: bool = Query(False),
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    from app.services.factory.acl_factory import check_read_access
    is_admin = db.execute(text(
        "SELECT 1 FROM usergroupmapping WHERE login=:l AND groupname='admin'"
    ), {"l": current_user.login}).first() is not None
    result = svc.filter_product_structure(db, ws, ci_id, configSpec, path, depth,
                                            user_login=current_user.login,
                                            is_admin=is_admin,
                                            link_type=linkType, diverge=diverge)
    if not result:
        raise HTTPException(status_code=404, detail="Product structure not found for this configuration item")
    return result[0]


@router.get("/workspaces/{ws}/products/{ci_id}/decode-path/{p:path}")
@router.get("/workspaces/{ws}/products/{ci_id}/decode-path/{p:path}/", include_in_schema=False)
def decode_path(ws: str, ci_id: str, p: str,
                current_user: Account = Depends(get_current_user),
                db: Session = Depends(get_db)):
    """P2-09: 返回 LightPartLinkDTO 列表（number/name/referenceDescription/fullId）。

    对齐 Java ProductResource.decodePath → LightPartLinkDTO(partNumber, partName,
    referenceDescription, fullId)。4 字段已完全匹配，无需修改。
    """
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
    """P2-07: 返回完整 ProductInstanceMasterDTO 列表（identifier + iteration + acl）。"""
    instances = svc.list_instances(db, ws)
    return [_build_instance_master_dict(db, i) for i in instances]


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
    return _build_instance_master_dict(db, inst)


@router.get("/workspaces/{ws}/product-instances/{pid}/instances", response_model=List[ProductInstanceDTO])
@router.get("/workspaces/{ws}/product-instances/{pid}/instances/", include_in_schema=False)
def list_ci_instances(ws: str, pid: str,
                       current_user: Account = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """P2-07: 返回完整 ProductInstanceMasterDTO 列表（identifier + iteration + acl）。"""
    instances = svc.list_instances(db, ws, pid)
    return [_build_instance_master_dict(db, i) for i in instances]


# ── Stubs ──

@router.get("/workspaces/{ws}/products/{ci_id}/releases/last")
@router.get("/workspaces/{ws}/products/{ci_id}/releases/last/", include_in_schema=False)
def last_release(ws: str, ci_id: str,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """返回 CI 根零件的最新已发布版本。"""
    ci = svc.get_ci(db, ws, ci_id)
    root_pn = ci.partmaster_partnumber
    rev = db.query(PartRevision).filter(
        PartRevision.workspace_id == ws,
        PartRevision.partmaster_partnumber == root_pn,
        PartRevision.status == 1,
    ).order_by(PartRevision.version.desc()).first()
    if rev is None:
        raise HTTPException(status_code=404, detail="No released revision for this configuration item")
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
        "checkOutDate": format_iso_date(rev.check_out_date),
        "releaseDate": format_iso_date(rev.release_date),
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
    ci = svc.get_ci(db, ws, ci_id)
    # PathDataMasterNotFoundException: 等待 PathData 域实现后抛出
    try:
        rows = db.execute(text(
            "SELECT DISTINCT pdm.path, pdm.id FROM pathdatamaster pdm "
            "JOIN prdinstiteration_pathdatamstr pipd ON pdm.id = pipd.pathdatamaster_id "
            "JOIN productinstanceiteration pii ON pii.workspace_id = pipd.workspace_id "
            "AND pii.configurationitem_id = pipd.configurationitem_id "
            "AND pii.prdinstancemaster_serialnumber = pipd.prdinstancemaster_serialnumber "
            "AND pii.iteration = pipd.prdinstanceiteration_iteration "
            "JOIN productinstancemaster pim ON pim.workspace_id = pii.workspace_id "
            "AND pim.configurationitem_id = pii.configurationitem_id "
            "AND pim.serialnumber = pii.prdinstancemaster_serialnumber "
            "WHERE pim.workspace_id = :ws AND pim.configurationitem_id = :ci"
        ), {"ws": ws, "ci": ci_id}).fetchall()
        return [{"id": r[1], "path": r[0]} for r in rows]
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to retrieve path choices")


@router.get("/workspaces/{ws}/products/{ci_id}/versions-choices")
@router.get("/workspaces/{ws}/products/{ci_id}/versions-choices/", include_in_schema=False)
def versions_choices(ws: str, ci_id: str,
                      current_user: Account = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    """返回 CI 根零件的所有版本列表。CI 不存在则返回空列表。"""
    ci = svc.get_ci(db, ws, ci_id)
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
    return [{"type": r[0]} for r in rows if r[0]]


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
    return [_p2p_svc._link_row_to_dict(r, db=db, ws=ws, ci_id=pid) for r in rows]


# ── Cascade ──

_part_svc = ProductService()


def _collect_ci_parts(db: Session, ws: str, ci_id: str,
                       config_spec=None, path=None, user_login=None,
                       diverge=False) -> list[PartRevision]:
    """递归收集 CI 装配结构中的所有 PartRevision（去重）。CI 不存在时返回空列表。
    支持按 configSpec 选择迭代，按 path 定位起始子树。
    """
    ci = svc.get_ci(db, ws, ci_id)
    root_pn = ci.partmaster_partnumber

    # 若提供 path（非空且非 -1），定位起始子树
    if path and path != '-1':
        decoded = svc.decode_path(db, ws, ci_id, path)
        if decoded:
            # 取最后一段的 number 作为遍历根
            root_pn = decoded[-1]["number"]

    master = db.query(PartMaster).filter(
        PartMaster.workspace_id == ws,
        PartMaster.number == root_pn,
    ).first()
    if not master or not master.revisions:
        return []
    seen: set[tuple] = set()
    collected: list[PartRevision] = []

    # 解析 configSpec → PS filter
    ps_filter = None
    if config_spec:
        ps_filter = svc.parse_config_spec_str(config_spec, db=db, user_login=user_login, diverge=diverge)

    def collect(rev: PartRevision):
        key = (rev.workspace_id, rev.partmaster_partnumber, rev.version)
        if key in seen:
            return
        seen.add(key)
        collected.append(rev)
        last_it = rev.last_iteration
        if last_it:
            for link in (last_it.components or []):
                child_master = db.query(PartMaster).filter(
                    PartMaster.workspace_id == link.component_workspace_id,
                    PartMaster.number == link.component_partnumber,
                ).first()
                if not child_master:
                    continue
                if ps_filter:
                    # 用 filter 选择迭代而非硬编码 last_revision
                    filtered = ps_filter.filter_part_iterations(child_master)
                    child_rev = filtered[0].revision if filtered else None
                else:
                    child_rev = child_master.last_revision
                if child_rev:
                    collect(child_rev)

    # 选择根 revision
    if ps_filter:
        filtered = ps_filter.filter_part_iterations(master)
        root_rev = filtered[0].revision if filtered else master.last_revision
    else:
        root_rev = master.last_revision
    if root_rev:
        collect(root_rev)
    return collected


@router.put("/workspaces/{ws}/products/{ci_id}/cascade-checkout")
@router.put("/workspaces/{ws}/products/{ci_id}/cascade-checkout/", include_in_schema=False)
def cascade_checkout(ws: str, ci_id: str,
                      configSpec: Optional[str] = Query(None, alias="configSpec"),
                      path: Optional[str] = Query(None),
                      current_user: Account = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    parts = _collect_ci_parts(db, ws, ci_id,
                               config_spec=configSpec, path=path,
                               user_login=current_user.login)
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
                     configSpec: Optional[str] = Query(None, alias="configSpec"),
                     path: Optional[str] = Query(None),
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    parts = _collect_ci_parts(db, ws, ci_id,
                               config_spec=configSpec, path=path,
                               user_login=current_user.login)
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
                          configSpec: Optional[str] = Query(None, alias="configSpec"),
                          path: Optional[str] = Query(None),
                          current_user: Account = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    parts = _collect_ci_parts(db, ws, ci_id,
                               config_spec=configSpec, path=path,
                               user_login=current_user.login)
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
             configSpec: Optional[str] = Query(None, alias="configSpec"),
             diverge: bool = Query(False),
             current_user: Account = Depends(get_current_user),
             db: Session = Depends(get_db)):
    """在装配结构中搜索路径（对齐 Java ProductResource.searchPaths）。"""
    import re
    from app.models.product import ConfigurationItem

    ci = svc.get_ci(db, ws, ci_id)
    root_master = (
        db.query(PartMaster)
        .filter(
            PartMaster.workspace_id == ws,
            PartMaster.number == ci.partmaster_partnumber,
        )
        .first()
    )
    if root_master is None:
        return []

    # 解析 configSpec → filter（用于选择迭代）
    ps_filter = None
    if configSpec:
        ps_filter = svc.parse_config_spec_str(configSpec, db=db, user_login=current_user.login, diverge=diverge)

    try:
        pattern = re.compile(search) if search else None
    except re.error:
        pattern = re.compile(re.escape(search)) if search else None

    collected: list[str] = []

    def walk(master, path_parts: list[str]):
        path_str = "-".join(path_parts)
        if pattern is None or (
            pattern.search(master.number or "")
            or pattern.search(master.name or "")
            or pattern.search(path_str)
        ):
            if path_str:
                collected.append(path_str)

        if not master.revisions:
            return
        if ps_filter:
            filtered = ps_filter.filter_part_iterations(master)
            last_it = filtered[0] if filtered else None
        else:
            last_rev = master.revisions[-1]
            last_it = last_rev.iterations[-1] if last_rev and last_rev.iterations else None

        if not last_it:
            return
        for link in (last_it.components or []):
            child_master = (
                db.query(PartMaster)
                .filter(
                    PartMaster.workspace_id == ws,
                    PartMaster.number == link.component_partnumber,
                )
                .first()
            )
            if child_master:
                child_path = path_parts + [str(link.id)]
                walk(child_master, child_path)

    walk(root_master, [])
    return [{"path": p} for p in collected]


@router.get("/workspaces/{ws}/products/{ci_id}/document-links/{pn}-{pv}-{pi}/{config_spec}")
@router.get("/workspaces/{ws}/products/{ci_id}/document-links/{pn}-{pv}-{pi}/{config_spec}/", include_in_schema=False)
def ci_document_links(ws: str, ci_id: str,
                       pn: str, pv: str, pi: int, config_spec: str,
                       current_user: Account = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """获取零件迭代在指定基线中关联的文档（对齐 Java ProductResource.getDocumentLinksForGivenPartIteration）。"""
    from app.models.configuration.product_baseline import ProductBaseline
    from app.models.configuration.baselined_document import BaselinedDocument
    from app.models.configuration.product_instance_iteration import ProductInstanceIteration
    from app.models.document.document_iteration import DocumentIteration
    from app.models.document.document_revision import DocumentRevision
    from app.models.document.document_link import DocumentLink

    # 1. 解析 config_spec → baseline
    baseline = None
    if config_spec.startswith("pi-"):
        serial_number = config_spec[3:]
        last_pii = db.query(ProductInstanceIteration).filter(
            ProductInstanceIteration.workspace_id == ws,
            ProductInstanceIteration.configurationitem_id == ci_id,
            ProductInstanceIteration.prdinstancemaster_serialnumber == serial_number,
        ).order_by(ProductInstanceIteration.iteration.desc()).first()
        if last_pii and last_pii.productbaseline_id:
            baseline = db.query(ProductBaseline).filter(
                ProductBaseline.id == last_pii.productbaseline_id,
            ).first()
    else:
        try:
            bl_id = int(config_spec)
            baseline = db.query(ProductBaseline).filter(
                ProductBaseline.id == bl_id,
            ).first()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid config_spec")

    if baseline is None:
        return []

    # 2. 获取 baseline 的 DocumentCollection 中的 BaselinedDocuments
    baselined_docs = db.query(BaselinedDocument).filter(
        BaselinedDocument.documentcollection_id == baseline.documentcollection_id,
    ).all() if baseline.documentcollection_id else []

    if not baselined_docs:
        return []

    # 3. 获取 PartIteration 的 linked documents（通过 partiteration_documentlink 关联表）
    pi_obj = db.query(PartIteration).filter(
        PartIteration.workspace_id == ws,
        PartIteration.partmaster_partnumber == pn,
        PartIteration.partrevision_version == pv,
        PartIteration.iteration == pi,
    ).first()

    if pi_obj is None:
        return []

    link_rows = db.execute(text("""
        SELECT documentlink_id FROM partiteration_documentlink
        WHERE workspace_id = :ws AND partmaster_partnumber = :pn
          AND partrevision_version = :pv AND iteration = :pi
    """), {"ws": ws, "pn": pn, "pv": pv, "pi": pi}).fetchall()

    if not link_rows:
        return []

    doc_links = db.query(DocumentLink).filter(
        DocumentLink.id.in_([r[0] for r in link_rows]),
    ).all() if link_rows else []

    # 4. 交叉匹配：BaselinedDocument targets × PartIteration document links
    result = []
    for bd in baselined_docs:
        target_rev = db.query(DocumentRevision).filter(
            DocumentRevision.workspace_id == bd.target_workspace_id,
            DocumentRevision.documentmaster_id == bd.target_documentmaster_id,
            DocumentRevision.version == bd.target_docrevision_version,
        ).first()
        if target_rev is None:
            continue

        for dl in doc_links:
            if (dl.target_workspace_id == bd.target_workspace_id
                    and dl.target_documentmaster_id == bd.target_documentmaster_id
                    and dl.target_docrevision_version == bd.target_docrevision_version):
                result.append({
                    "documentMasterId": bd.target_documentmaster_id,
                    "version": bd.target_docrevision_version,
                    "title": target_rev.title or "",
                    "iteration": bd.target_iteration,
                    "workspaceId": bd.target_workspace_id,
                    "commentLink": dl.comment or "",
                })

    return result


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
