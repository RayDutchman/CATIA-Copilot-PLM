"""Context 产品分解结构（PBS）过滤（对齐 Payara ProductManagerBean.filterProductBreakdownStructure）。

对查询的每个 QueryContext（配置项 + 可选序列号），用 PSFilterVisitor 遍历装配结构，
构建 QueryResultRow（含 depth/amount/path/P2P/context），并按 pathDataQueryRule 过滤路径。
merge_rows 取 PBS 结果与 PartRevision 查询结果的交集。
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.product.part_master import PartMaster
from app.models.product.part_substitute_link import PartSubstituteLink
from app.services.query_executor import run_pathdata_query


def _path_string(path_links) -> str:
    """把 Component.path（链接链）编码为 pathdatamaster.path 格式 "-1-u2-u5"。"""
    parts = ["-1"]
    for link in path_links[1:]:  # 跳过虚拟根链接
        prefix = "s" if isinstance(link, PartSubstituteLink) else "u"
        parts.append(f"{prefix}{link.id}")
    return "-".join(parts)


def _amount(path_links) -> float:
    """路径各链接 amount 累乘（跳过 unit 非空的，对齐 Java）。"""
    amt = 1.0
    for link in path_links:
        if getattr(link, "unit", None) is None:
            amt *= (getattr(link, "amount", 1.0) or 1.0)
    return amt


def _p2p_for_path(p2p_links, path_str):
    """按路径匹配 P2P 链接 → (sources, targets)，各为 {type: [对端 path]}。"""
    sources, targets = {}, {}
    for sp, tp, typ in p2p_links:
        if sp == path_str:
            sources.setdefault(typ, []).append(tp)
        if tp == path_str:
            targets.setdefault(typ, []).append(sp)
    return sources, targets


def _walk(comp, rows, ci_id, serial, ws, p2p_links, allowed_paths):
    """递归遍历 Component 树，收集 QueryResultRow。"""
    path_str = _path_string(comp.path)
    rev = comp.retained_iteration.revision if comp.retained_iteration else None
    if rev is not None and (allowed_paths is None or path_str in allowed_paths):
        sources, targets = _p2p_for_path(p2p_links, path_str)
        rows.append({
            "partRevision": rev,
            "depth": len(comp.path) - 1,
            "amount": _amount(comp.path),
            "context": {"configurationItemId": ci_id, "serialNumber": serial,
                        "workspaceId": ws},
            "path": path_str,
            "sources": sources,
            "targets": targets,
        })
    for child in comp.components:
        _walk(child, rows, ci_id, serial, ws, p2p_links, allowed_paths)


def filter_pbs(db: Session, workspace_id: str, query: dict,
               user_login: str, is_admin: bool = False) -> list:
    """遍历每个 context 的产品结构，返回 QueryResultRow 列表。"""
    from app.services.product_structure import ProductStructureService
    from app.services.configuration import PSFilterVisitor

    pss = ProductStructureService()
    rows = []
    pathdata_rule = query.get("pathDataQueryRule")
    for ctx in (query.get("contexts") or []):
        ci_id = ctx.get("configurationItemId")
        serial = ctx.get("serialNumber")
        if not ci_id:
            continue
        try:
            ci = pss.get_ci(db, workspace_id, ci_id)
        except Exception:
            continue  # CI 不存在 → 跳过该 context
        root_pm = db.query(PartMaster).filter(
            PartMaster.workspace_id == workspace_id,
            PartMaster.number == ci.partmaster_partnumber,
        ).first()
        if root_pm is None or not root_pm.revisions:
            continue
        # 配置规格：有序列号用产品实例基线，否则用最新
        config_spec_str = f"pi-{serial}" if serial else "latest"
        try:
            config_spec = pss.parse_config_spec_str(
                config_spec_str, db=db, user_login=user_login)
        except Exception:
            config_spec = pss.parse_config_spec_str(
                "latest", db=db, user_login=user_login)

        visitor = PSFilterVisitor(db, workspace_id, config_spec)
        root_comp = visitor.visit_from_master(root_pm)

        # 该 CI 的 P2P 链接
        p2p_links = db.execute(text(
            "SELECT p.sourcepath, p.targetpath, p.type FROM pathtopathlink p "
            "JOIN configurationitem_p2plink cp ON cp.pathtopathlink_id = p.id "
            "WHERE cp.workspace_id = :ws AND cp.configurationitem_id = :ci"
        ), {"ws": workspace_id, "ci": ci_id}).fetchall()

        # pathData 规则过滤（仅当有 pathDataQueryRule 且指定了序列号/产品实例）
        allowed_paths = None
        if pathdata_rule and serial:
            pii_iter = db.execute(text(
                "SELECT max(iteration) FROM productinstanceiteration "
                "WHERE workspace_id = :ws AND configurationitem_id = :ci "
                "AND prdinstancemaster_serialnumber = :sn"
            ), {"ws": workspace_id, "ci": ci_id, "sn": serial}).scalar()
            if pii_iter is not None:
                allowed_paths = run_pathdata_query(db, {
                    "workspace_id": workspace_id, "configurationitem_id": ci_id,
                    "serialnumber": serial, "iteration": pii_iter,
                }, pathdata_rule)

        _walk(root_comp, rows, ci_id, serial, workspace_id, p2p_links, allowed_paths)
    return rows


def merge_rows(pbs_rows: list, part_revisions: list) -> list:
    """取 PBS 行与 PartRevision 查询结果的交集（对齐 QueryResult.mergeRows）。"""
    keyset = {
        (pr.workspace_id, pr.partmaster_partnumber, pr.version)
        for pr in part_revisions
    }
    result = []
    for r in pbs_rows:
        pr = r["partRevision"]
        if (pr.workspace_id, pr.partmaster_partnumber, pr.version) in keyset:
            result.append(r)
    return result
