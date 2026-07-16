"""产品端点路由（ConfigurationItem CRUD + 产品实例）。"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.core.exceptions import (
    ConfigurationItemNotFoundException,
    ProductInstanceMasterNotFoundException,
)
from app.models.product import ProductInstanceMaster
from app.services.product_structure import ProductStructureService
from app.services.product_manager import ProductService
from app.services.cascade_action_manager import cascade_action_service
from app.schemas.product import ConfigurationItemDTO, ProductInstanceDTO

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
svc = ProductStructureService()

# 注意：_NAME_CACHE 无 TTL 和容量上限，长期运行可能持续增长。
# 考虑到此服务部署在 Docker 容器内、用户数据量有限，当前风险可控。
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


# ── Products（CI CRUD）──

@router.get("/workspaces/{ws}/products", response_model=List[ConfigurationItemDTO])
@router.get("/workspaces/{ws}/products/", include_in_schema=False)
def list_cis(ws: str, current_user: Account = Depends(get_current_user),
             db: Session = Depends(get_db)):
    cis = svc.list_cis(db, ws)
    return [svc.build_ci_dto(db, c) for c in cis]


@router.get("/workspaces/{ws}/products/numbers")
@router.get("/workspaces/{ws}/products/numbers/", include_in_schema=False)
def search_ci_numbers(ws: str, q: str = Query(""),
                      current_user: Account = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    cis = svc.search_numbers(db, ws, q)
    return [svc.build_ci_dto(db, c) for c in cis]


@router.post("/workspaces/{ws}/products", status_code=201, response_model=ConfigurationItemDTO)
@router.post("/workspaces/{ws}/products/", status_code=201, include_in_schema=False)
def create_ci(ws: str, body: dict,
              current_user: Account = Depends(get_current_user),
              db: Session = Depends(get_db)):
    ci_id = body.get("id", body.get("reference", ""))
    desc = body.get("description", "")
    part = body.get("designItemNumber", body.get("partNumber", body.get("partMasterNumber", "")))
    ci = svc.create_ci(db, ws, ci_id, desc, part, current_user.login)
    return svc.build_ci_dto(db, ci)


@router.get("/workspaces/{ws}/products/{ci_id}", response_model=ConfigurationItemDTO)
@router.get("/workspaces/{ws}/products/{ci_id}/", include_in_schema=False)
def get_ci(ws: str, ci_id: str,
           current_user: Account = Depends(get_current_user),
           db: Session = Depends(get_db)):
    ci = svc.get_ci(db, ws, ci_id)
    return svc.build_ci_dto(db, ci)


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
    return svc.build_ci_dto(db, ci)


@router.get("/workspaces/{ws}/products/{ci_id}/filter")
@router.get("/workspaces/{ws}/products/{ci_id}/filter/", include_in_schema=False)
def filter_structure(ws: str, ci_id: str,
                     configSpec: str = Query(None), path: str = Query(None),
                     depth: int = Query(None),
                     linkType: Optional[str] = Query(None),
                     diverge: bool = Query(False),
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    is_admin = db.execute(text(
        "SELECT 1 FROM usergroupmapping WHERE login=:l AND groupname='admin'"
    ), {"l": current_user.login}).first() is not None
    result = svc.filter_product_structure(db, ws, ci_id, configSpec, path, depth,
                                            user_login=current_user.login,
                                            is_admin=is_admin,
                                            link_type=linkType, diverge=diverge)
    if not result:
        raise ConfigurationItemNotFoundException("ConfigurationItemNotFoundException", ci_id)
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
    return svc.flatten_bom_to_part_list(result, ws, ci_id)


# ── Product Instances ──

@router.get("/workspaces/{ws}/product-instances", response_model=List[ProductInstanceDTO])
@router.get("/workspaces/{ws}/product-instances/", include_in_schema=False)
def list_product_instances(ws: str,
                            current_user: Account = Depends(get_current_user),
                            db: Session = Depends(get_db)):
    """P2-07: 返回完整 ProductInstanceMasterDTO 列表（identifier + iteration + acl）。"""
    from app.services.products.product_instance_manager import product_instance_service
    instances = svc.list_instances(db, ws)
    return [product_instance_service.build_master_dto(db, i, svc=svc) for i in instances]


@router.get("/workspaces/{ws}/product-instances/{sn}", response_model=ProductInstanceDTO)
@router.get("/workspaces/{ws}/product-instances/{sn}/", include_in_schema=False)
def get_product_instance(ws: str, sn: str,
                          current_user: Account = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    from app.services.products.product_instance_manager import product_instance_service
    inst = db.query(ProductInstanceMaster).filter(
        ProductInstanceMaster.workspace_id == ws,
        ProductInstanceMaster.serialnumber == sn,
    ).first()
    if not inst:
        raise ProductInstanceMasterNotFoundException("ProductInstanceMasterNotFoundException", sn)
    return product_instance_service.build_master_dto(db, inst, svc=svc)


@router.get("/workspaces/{ws}/product-instances/{pid}/instances", response_model=List[ProductInstanceDTO])
@router.get("/workspaces/{ws}/product-instances/{pid}/instances/", include_in_schema=False)
def list_ci_instances(ws: str, pid: str,
                       current_user: Account = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """P2-07: 返回完整 ProductInstanceMasterDTO 列表（identifier + iteration + acl）。"""
    from app.services.products.product_instance_manager import product_instance_service
    instances = svc.list_instances(db, ws, pid)
    return [product_instance_service.build_master_dto(db, i, svc=svc) for i in instances]


# ── Stubs ──

@router.get("/workspaces/{ws}/products/{ci_id}/releases/last")
@router.get("/workspaces/{ws}/products/{ci_id}/releases/last/", include_in_schema=False)
def last_release(ws: str, ci_id: str,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """返回 CI 根零件的最新已发布版本。"""
    try:
        return svc.get_last_release_dto(db, ws, ci_id)
    except Exception:
        raise


@router.get("/workspaces/{ws}/products/{ci_id}/path-choices")
@router.get("/workspaces/{ws}/products/{ci_id}/path-choices/", include_in_schema=False)
def path_choices(ws: str, ci_id: str,
                 type: str = Query(""),
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    """返回 CI 下已存在的路径数据列表。CI 不存在则返回 404（对齐 Java getConfigurationItem）。"""
    exists = db.execute(text(
        "SELECT 1 FROM configurationitem WHERE workspace_id=:ws AND id=:ci"
    ), {"ws": ws, "ci": ci_id}).first()
    if not exists:
        raise ConfigurationItemNotFoundException("ConfigurationItemNotFoundException", ci_id)
    return svc.get_path_choices(db, ws, ci_id)


@router.get("/workspaces/{ws}/products/{ci_id}/versions-choices")
@router.get("/workspaces/{ws}/products/{ci_id}/versions-choices/", include_in_schema=False)
def versions_choices(ws: str, ci_id: str,
                      current_user: Account = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    """返回 CI 根零件的所有版本列表。CI 不存在则返回空列表。"""
    return svc.get_versions_choices(db, ws, ci_id)


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
    from app.services.products.path_to_path_service import path_to_path_service
    types = path_to_path_service.get_link_types_for_ci(db, ws, pid)
    return [{"type": t} for t in types]


@router.get("/workspaces/{ws}/products/{pid}/path-to-path-links/source/{source:path}/target/{target:path}")
@router.get("/workspaces/{ws}/products/{pid}/path-to-path-links/source/{source:path}/target/{target:path}/", include_in_schema=False)
def path_to_path_links_detail(ws: str, pid: str, source: str, target: str,
                               current_user: Account = Depends(get_current_user),
                               db: Session = Depends(get_db)):
    """返回 CI 下指定源→目标路径的链接列表。

    对齐 Payara ProductManagerBean.getPathToPathLinkFromSourceAndTarget()。
    """
    from app.services.products.path_to_path_service import path_to_path_service
    return path_to_path_service.get_links_from_source_and_target(db, ws, pid, source, target)


# ── Cascade ──

_part_svc = ProductService()


@router.put("/workspaces/{ws}/products/{ci_id}/cascade-checkout")
@router.put("/workspaces/{ws}/products/{ci_id}/cascade-checkout/", include_in_schema=False)
def cascade_checkout(ws: str, ci_id: str,
                      configSpec: Optional[str] = Query(None, alias="configSpec"),
                      path: Optional[str] = Query(None),
                      current_user: Account = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    parts = cascade_action_service.collect_ci_parts(
        svc, db, ws, ci_id,
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
    parts = cascade_action_service.collect_ci_parts(
        svc, db, ws, ci_id,
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
    parts = cascade_action_service.collect_ci_parts(
        svc, db, ws, ci_id,
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
    return svc.search_ci_paths(db, ws, ci_id, search=search,
                                 config_spec=configSpec, diverge=diverge,
                                 user_login=current_user.login)


@router.get("/workspaces/{ws}/products/{ci_id}/document-links/{pn}-{pv}-{pi}/{config_spec}")
@router.get("/workspaces/{ws}/products/{ci_id}/document-links/{pn}-{pv}-{pi}/{config_spec}/", include_in_schema=False)
def ci_document_links(ws: str, ci_id: str,
                       pn: str, pv: str, pi: int, config_spec: str,
                       current_user: Account = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """获取零件迭代在指定基线中关联的文档（对齐 Java ProductResource.getDocumentLinksForGivenPartIteration）。"""
    return svc.get_ci_document_links(db, ws, ci_id, pn, pv, pi, config_spec)


@router.get("/workspaces/{ws}/products/{ci_id}/document-links/{pn}/{config_spec}")
@router.get("/workspaces/{ws}/products/{ci_id}/document-links/{pn}/{config_spec}/", include_in_schema=False)
def ci_document_links_wip(ws: str, ci_id: str, pn: str, config_spec: str,
                           current_user: Account = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    """返回 CI 下指定零件的最新 document-links（WIP 配置规约）。"""
    return svc.get_ci_document_links_wip(db, ws, ci_id, pn, config_spec)


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
