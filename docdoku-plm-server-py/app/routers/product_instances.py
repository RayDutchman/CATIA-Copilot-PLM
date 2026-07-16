"""产品实例端点（ProductInstancesResource）。

GET /products/{ci_id}/instances?configSpec=wip → 3D 实例数据（对齐 Java ProductResource.getFilteredInstances）
GET /products/{ci_id}/instances            → 产品实例序列号列表（对齐 Java ProductResource.getInstances）
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import (
    EntityNotFoundException,
    ProductInstanceIterationNotFoundException,
    ProductInstanceMasterNotFoundException,
)
from app.models.auth import Account
from app.models.product.part_iteration import PartIteration
from app.services.product_structure import ProductStructureService
from app.services.products.product_instance_manager import product_instance_service
from app.services.file_export.instance_body_writer_tools import (
    identity_matrix, collect_leaf_instances,
)
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


@router.get("/workspaces/{ws}/products/{ci_id}/instances")
@router.get("/workspaces/{ws}/products/{ci_id}/instances/", include_in_schema=False)
def list_instances(ws: str, ci_id: str,
                   configSpec: Optional[str] = Query(None, alias="configSpec"),
                   path: Optional[str] = Query(None),
                   diverge: bool = Query(False),
                   current_user: Account = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """产品实例列表。

    无 configSpec → 返回 ProductInstanceMaster 序列号列表（产品实例管理）。
    有 configSpec → 返回 3D 实例数据（矩阵 + files + bbox），对齐 Java getFilteredInstances。
    """
    if not configSpec:
        return product_instance_service.list_instances(db, ws, ci_id)

    # 3D 实例模式：对齐 Java ProductResource.getFilteredInstances
    from app.models.product.configuration_item import ConfigurationItem
    from app.models.part import PartMaster
    ci = db.query(ConfigurationItem).filter(
        ConfigurationItem.workspace_id == ws,
        ConfigurationItem.id == ci_id,
    ).first()
    if not ci or not ci.partmaster_partnumber:
        return []

    # 解析 configSpec → PS filter
    ps_filter = None
    if configSpec.startswith("pi-"):
        # pi-{serial} → 解析该实例基线的 baselinedpart 过滤（对齐 Java PSFilterManagerBean）
        ps_filter = svc.parse_config_spec_str(
            configSpec, db=db, user_login=current_user.login, diverge=diverge,
            ws=ws, ci_id=ci_id)
    else:
        ps_filter = svc.parse_config_spec_str(configSpec, db=db, user_login=current_user.login, diverge=diverge)

    # 选择 root part iteration
    root_part_master = db.query(PartMaster).filter(
        PartMaster.workspace_id == ws,
        PartMaster.number == ci.partmaster_partnumber,
    ).first()
    if not root_part_master:
        return []

    if ps_filter:
        filtered = ps_filter.filter_part_iterations(root_part_master)
        root_pi = filtered[0] if filtered else None
    else:
        root_pi = db.query(PartIteration).filter(
            PartIteration.workspace_id == ws,
            PartIteration.partmaster_partnumber == ci.partmaster_partnumber,
        ).order_by(PartIteration.iteration.desc()).first()

    if not root_pi:
        return []

    # 若指定 path 且不是 -1，导航到该子树
    instance_ids = [-1]  # 虚拟根
    if path and path != '-1':
        segments = [s for s in path.split('-') if s.startswith(('u', 's')) and s[1:].isdigit()]
        for seg in segments:
            instance_ids.append(int(seg[1:]))
        if segments:
            from app.models.product.part_usage_link import PartUsageLink
            link_id = int(segments[-1][1:])
            link = db.query(PartUsageLink).filter(PartUsageLink.id == link_id).first()
            if link:
                child_pm = db.query(PartMaster).filter(
                    PartMaster.workspace_id == link.component_workspace_id,
                    PartMaster.number == link.component_partnumber,
                ).first()
                if child_pm and ps_filter:
                    child_filtered = ps_filter.filter_part_iterations(child_pm)
                    if child_filtered:
                        root_pi = child_filtered[0]
                elif child_pm:
                    child_pi = db.query(PartIteration).filter(
                        PartIteration.workspace_id == link.component_workspace_id,
                        PartIteration.partmaster_partnumber == link.component_partnumber,
                    ).order_by(PartIteration.iteration.desc()).first()
                    if child_pi:
                        root_pi = child_pi

    result: list[dict] = []
    collect_leaf_instances(db, root_pi, identity_matrix(), instance_ids, result, ps_filter=ps_filter)
    return result


@router.post("/workspaces/{ws}/products/{ci_id}/instances", status_code=201)
@router.post("/workspaces/{ws}/products/{ci_id}/instances/", status_code=201, include_in_schema=False)
def create_instance(ws: str, ci_id: str, body: dict,
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    inst = product_instance_service.create_instance(db, ws, ci_id, body.get("serialNumber", ""),
                                                     body.get("baselineId", 0), current_user.login)
    return inst


# 对齐 Java ProductResource.getInstancesForMultiplePath
@router.post("/workspaces/{ws}/products/{ci_id}/instances/paths", status_code=200)
@router.post("/workspaces/{ws}/products/{ci_id}/instances/paths/", status_code=200, include_in_schema=False)
def instances_for_multiple_paths(ws: str, ci_id: str, body: dict,
                                  current_user: Account = Depends(get_current_user),
                                  db: Session = Depends(get_db)):
    """按多路径批量收集 3D 实例数据（对齐 Java getInstancesForMultiplePath）。"""
    from app.models.product.configuration_item import ConfigurationItem
    from app.models.part import PartMaster, PartUsageLink

    config_spec = body.get("configSpec", "")
    paths = body.get("paths", [])
    body_diverge = body.get("diverge", False)

    ci = db.query(ConfigurationItem).filter(
        ConfigurationItem.workspace_id == ws,
        ConfigurationItem.id == ci_id,
    ).first()
    if not ci or not ci.partmaster_partnumber:
        return []

    ps_filter = None
    if config_spec:
        if config_spec.startswith("pi-"):
            ps_filter = svc.parse_config_spec_str(
                config_spec, db=db, user_login=current_user.login, diverge=body_diverge,
                ws=ws, ci_id=ci_id)
        else:
            ps_filter = svc.parse_config_spec_str(config_spec, db=db, user_login=current_user.login, diverge=body_diverge)

    root_part_master = db.query(PartMaster).filter(
        PartMaster.workspace_id == ws,
        PartMaster.number == ci.partmaster_partnumber,
    ).first()

    all_results: list[dict] = []
    for p in (paths or []):
        try:
            decoded = svc.decode_path(db, ws, ci_id, p)
            if not decoded:
                continue
            target_pn = decoded[-1]["number"]
            target_pm = db.query(PartMaster).filter(
                PartMaster.workspace_id == ws,
                PartMaster.number == target_pn,
            ).first()
            if not target_pm:
                continue
            if ps_filter:
                filtered = ps_filter.filter_part_iterations(target_pm)
                root_pi = filtered[0] if filtered else None
            else:
                root_pi = db.query(PartIteration).filter(
                    PartIteration.workspace_id == ws,
                    PartIteration.partmaster_partnumber == target_pn,
                ).order_by(PartIteration.iteration.desc()).first()
            if not root_pi:
                continue
            instance_ids = [-1]
            segments = [s for s in p.split('-') if s.startswith(('u', 's')) and s[1:].isdigit()]
            for seg in segments:
                instance_ids.append(int(seg[1:]))
            result: list[dict] = []
            collect_leaf_instances(db, root_pi, identity_matrix(), instance_ids, result, ps_filter=ps_filter)
            all_results.extend(result)
        except Exception:
            # 跳过失败的 path，不整体 500
            continue
    return all_results


@router.put("/workspaces/{ws}/products/{ci_id}/instances/{sn}")
@router.put("/workspaces/{ws}/products/{ci_id}/instances/{sn}/", include_in_schema=False)
@router.put("/workspaces/{ws}/products/{ci_id}/instances/{sn}/iterations/{iteration}")
@router.put("/workspaces/{ws}/products/{ci_id}/instances/{sn}/iterations/{iteration}/", include_in_schema=False)
def update_instance(ws: str, ci_id: str, sn: str, body: dict,
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db),
                    iteration: int = None):
    return product_instance_service.update_instance(
        db, ws, ci_id, sn, body, current_user.login, iteration)


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
        raise ProductInstanceIterationNotFoundException(
            "ProductInstanceIterationNotFoundException", sn, str(it))
    doc_rows = db.execute(sql_text(
        "SELECT dl.id, dl.target_workspace_id, dl.target_documentmaster_id, "
        "dl.target_docrevision_version, dl.commentdata "
        "FROM prdinstiteration_documentlink pidl "
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


@router.delete("/workspaces/{ws}/products/{ci_id}/instances/{sn}", status_code=204)
def delete_instance(ws: str, ci_id: str, sn: str,
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    product_instance_service.delete_instance(db, ws, ci_id, sn)
    return Response(status_code=204)


@router.put("/workspaces/{ws}/products/{ci_id}/instances/{sn}/acl")
def update_instance_acl(ws: str, ci_id: str, sn: str, body: dict,
                        db: Session = Depends(get_db),
                        current_user: Account = Depends(get_current_user)):
    from app.services.factory.acl_factory import apply_acl
    from app.models.product import ProductInstanceMaster
    inst = db.query(ProductInstanceMaster).filter(
        ProductInstanceMaster.workspace_id == ws,
        ProductInstanceMaster.configurationitem_id == ci_id,
        ProductInstanceMaster.serialnumber == sn,
    ).first()
    if not inst:
        raise ProductInstanceMasterNotFoundException("ProductInstanceMasterNotFoundException", sn)
    user_entries = body.get("userEntries", {})
    group_entries = body.get("groupEntries", {})
    if not user_entries and not group_entries:
        inst.acl_id = None
        db.commit()
        return {"aclId": None}
    new_acl_id = apply_acl(db, inst.acl_id, user_entries, group_entries, workspace_id=ws)
    inst.acl_id = new_acl_id
    db.commit()
    return {"aclId": new_acl_id}


@router.put("/workspaces/{ws}/products/{ci_id}/instances/{sn}/rebase", status_code=204)
def rebase_instance(ws: str, ci_id: str, sn: str,
                    body: dict = None,
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    """产品实例换基线（对齐 Java ProductInstanceManagerBean.rebaseProductInstance）。

    简化实现：仅创建新迭代 + 关联新 baseline + 继承 iterationNote，
    未深拷贝 pathData / documentCollection / partCollection。
    """
    from fastapi.responses import Response

    # 解析新基线 ID
    baseline_id = body.get("id") if body else None
    if not baseline_id:
        raise HTTPException(400, "Missing baseline id in request body")

    product_instance_service.rebase_instance(
        db, ws, ci_id, sn, baseline_id, current_user.login)
    return Response(status_code=204)


# ══════════════════════════════════════════════════════════
# PathData 端点
# ══════════════════════════════════════════════════════════

from app.services.products.path_data_service import path_data_service


@router.get("/workspaces/{ws}/products/{ci_id}/instances/{sn}/pathdata/{path:path}")
@router.get("/workspaces/{ws}/products/{ci_id}/instances/{sn}/pathdata/{path:path}/", include_in_schema=False)
def get_path_data(ws: str, ci_id: str, sn: str, path: str,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """按路径字符串获取 PathDataMaster（找不到返回空 DTO，不报 404）。"""
    master = path_data_service.get_path_data_by_path(db, ws, ci_id, sn, path)
    if not master:
        # 对齐 Java：找不到返回空 DTO，包含路径信息
        return {
            "id": None,
            "path": path,
            "serialNumber": sn,
            "partLinksList": None,
            "pathDataIterations": [],
            "partAttributes": [],
            "partAttributeTemplates": [],
        }
    return path_data_service._build_master_dict(db, ws, ci_id, sn, master["id"])


@router.post("/workspaces/{ws}/products/{ci_id}/instances/{sn}/pathdata/{path:path}/new", status_code=201)
@router.post("/workspaces/{ws}/products/{ci_id}/instances/{sn}/pathdata/{path:path}/new/", status_code=201, include_in_schema=False)
def create_path_data_master(ws: str, ci_id: str, sn: str, path: str,
                             body: dict = None,
                             current_user: Account = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    """创建 PathDataMaster（含首迭代）。若同路径 master 已存在则追加迭代。"""
    body = body or {}
    attrs = body.get("instanceAttributes", [])
    note = body.get("iterationNote", "")
    return path_data_service.create_path_data_master(db, ws, ci_id, sn, path, attrs, note)


@router.post("/workspaces/{ws}/products/{ci_id}/instances/{sn}/pathdata/{master_id}", status_code=201)
@router.post("/workspaces/{ws}/products/{ci_id}/instances/{sn}/pathdata/{master_id}/", status_code=201, include_in_schema=False)
def add_path_data_iteration(ws: str, ci_id: str, sn: str, master_id: int,
                             body: dict = None,
                             current_user: Account = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    """向已有 PathDataMaster 追加新迭代。"""
    body = body or {}
    attrs = body.get("instanceAttributes", [])
    note = body.get("iterationNote", "")
    linked_docs = body.get("linkedDocuments", [])
    return path_data_service.add_new_path_data_iteration(
        db, ws, ci_id, sn, master_id, attrs, note, linked_docs
    )


@router.put("/workspaces/{ws}/products/{ci_id}/instances/{sn}/pathdata/{master_id}/iterations/{iteration}")
@router.put("/workspaces/{ws}/products/{ci_id}/instances/{sn}/pathdata/{master_id}/iterations/{iteration}/", include_in_schema=False)
def update_path_data(ws: str, ci_id: str, sn: str, master_id: int, iteration: int,
                     body: dict = None,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    """更新 PathDataIteration 的属性/备注/文档链接。"""
    body = body or {}
    attrs = body.get("instanceAttributes", [])
    note = body.get("iterationNote", "")
    linked_docs = body.get("linkedDocuments")
    return path_data_service.update_path_data(
        db, ws, ci_id, sn, master_id, iteration, attrs, note, linked_docs
    )


@router.delete("/workspaces/{ws}/products/{ci_id}/instances/{sn}/pathdata/{master_id}", status_code=204)
@router.delete("/workspaces/{ws}/products/{ci_id}/instances/{sn}/pathdata/{master_id}/", status_code=204, include_in_schema=False)
def delete_path_data(ws: str, ci_id: str, sn: str, master_id: int,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    """删除 PathDataMaster 及其所有迭代。"""
    from fastapi.responses import Response
    path_data_service.delete_path_data(db, ws, ci_id, sn, master_id)
    return Response(status_code=204)


@router.put("/workspaces/{ws}/products/{ci_id}/instances/{sn}/pathdata/{master_id}/iterations/{iteration}/files/{file_name}")
def rename_path_data_file(ws: str, ci_id: str, sn: str, master_id: int,
                           iteration: int, file_name: str,
                           body: dict = None,
                           current_user: Account = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    """重命名 PathDataIteration 附件（文件名变更）。"""
    import os
    from app.services.binary_storage import _vault_root
    body = body or {}
    new_name = body.get("name", file_name)
    vault_dir = _vault_root() / ws / "product-instances" / sn / "pathdata" / str(master_id) / "iterations" / str(iteration)
    old_path = vault_dir / file_name
    new_path = vault_dir / new_name
    try:
        if old_path.exists():
            old_path.rename(new_path)
    except Exception:
        pass  # 文件不存在时静默忽略
    return {"name": new_name, "fullName": str(new_path)}


@router.delete("/workspaces/{ws}/products/{ci_id}/instances/{sn}/pathdata/{master_id}/iterations/{iteration}/files/{file_name}", status_code=204)
def delete_path_data_file(ws: str, ci_id: str, sn: str, master_id: int,
                           iteration: int, file_name: str,
                           current_user: Account = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    """删除 PathDataIteration 附件。"""
    import os
    from fastapi.responses import Response
    from app.services.binary_storage import _vault_root
    vault_path = _vault_root() / ws / "product-instances" / sn / "pathdata" / str(master_id) / "iterations" / str(iteration) / file_name
    try:
        if vault_path.exists():
            vault_path.unlink()
    except Exception:
        pass
    return Response(status_code=204)


# ══════════════════════════════════════════════════════════
# PathToPathLink 实例级端点
# ══════════════════════════════════════════════════════════

from app.services.products.path_to_path_service import path_to_path_service


@router.get("/workspaces/{ws}/products/{ci_id}/instances/{sn}/path-to-path-links-types")
def instance_p2p_link_types(ws: str, ci_id: str, sn: str,
                             current_user: Account = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    """获取产品实例的所有 PathToPathLink 类型列表。"""
    types = path_to_path_service.get_link_types_for_instance(db, ws, ci_id, sn)
    return [{"type": t} for t in types]


@router.get("/workspaces/{ws}/products/{ci_id}/instances/{sn}/path-to-path-links")
def instance_p2p_links(ws: str, ci_id: str, sn: str,
                        current_user: Account = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    """获取产品实例的所有 PathToPathLink。"""
    return path_to_path_service.get_links_for_instance(db, ws, ci_id, sn)


@router.get("/workspaces/{ws}/products/{ci_id}/instances/{sn}/path-to-path-links/{link_id}")
def instance_p2p_link_by_id(ws: str, ci_id: str, sn: str, link_id: int,
                              current_user: Account = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    """按 ID 获取单个 PathToPathLink。"""
    from app.core.exceptions import PathToPathLinkNotFoundException
    link = path_to_path_service.get_link_by_id(db, link_id)
    if not link:
        raise PathToPathLinkNotFoundException("PathToPathLinkNotFoundException", str(link_id))
    return link


@router.get("/workspaces/{ws}/products/{ci_id}/instances/{sn}/path-to-path-links/source/{source_path:path}/target/{target_path:path}")
def instance_p2p_links_by_source_target(ws: str, ci_id: str, sn: str,
                                         source_path: str, target_path: str,
                                         current_user: Account = Depends(get_current_user),
                                         db: Session = Depends(get_db)):
    """按 sourcePath + targetPath 筛选实例级 PathToPathLink。"""
    return path_to_path_service.get_links_from_source_and_target_for_instance(
        db, ws, ci_id, sn, source_path, target_path
    )


@router.get("/workspaces/{ws}/products/{ci_id}/instances/{sn}/path-to-path-links-roots/{link_type}")
def instance_p2p_root_links(ws: str, ci_id: str, sn: str, link_type: str,
                              current_user: Account = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    """获取实例级指定类型的根 PathToPathLink。"""
    return path_to_path_service.get_root_links_for_instance(db, ws, ci_id, sn, link_type)


@router.get("/workspaces/{ws}/products/{ci_id}/instances/{sn}/link-path-part/{path_part:path}")
def instance_link_path_part(ws: str, ci_id: str, sn: str, path_part: str,
                              current_user: Account = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    """从路径字符串解析末级 PartMaster 信息。"""
    decoded = svc.decode_path(db, ws, ci_id, path_part)
    # 返回末级 link 的 component 信息
    last = decoded[-1]
    return last
