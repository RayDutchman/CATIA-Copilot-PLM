"""产品基线（ProductBaseline）端点路由。"""
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.models.product import ProductBaseline, ConfigurationItem
from app.models.part import PartRevision
from app.services.product_structure import ProductStructureService
from app.services.products.product_baseline_manager import product_baseline_service
from app.schemas.product import ProductBaselineSummaryDTO, ProductBaselineDetailDTO

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
svc = ProductStructureService()

_TYPE_MAP = {"LATEST": 0, "RELEASED": 1, "EFFECTIVE_DATE": 2,
             "EFFECTIVE_SERIAL_NUMBER": 3, "EFFECTIVE_LOT_ID": 4}
# 输出端：int ordinal → Payara ProductBaselineType 枚举名（对齐 JSON-B enum 序列化，前端按字符串判断）
_TYPE_NAME = {0: "LATEST", 1: "RELEASED", 2: "EFFECTIVE_DATE",
              3: "EFFECTIVE_SERIAL_NUMBER", 4: "EFFECTIVE_LOT_ID"}


def _type_name(t):
    """基线 type 整数 → Payara 枚举名字符串。"""
    if t is None:
        return None
    return _TYPE_NAME.get(t, "LATEST")


def _parse_iso_date(val):
    """ISO 字符串 → datetime，解析失败返回 None。"""
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
    return val


def _ci_latest_revision(db: Session, ws: str, ci_id: str) -> str | None:
    """查询 CI 根零件的最新版本号（对齐 Payara getDesignItem().getLastRevision().getVersion()，返回版本字符串）。"""
    ci = db.query(ConfigurationItem).filter(
        ConfigurationItem.workspace_id == ws,
        ConfigurationItem.id == ci_id,
    ).first()
    if not ci or not ci.partmaster_partnumber:
        return None
    rev = db.query(PartRevision).filter(
        PartRevision.workspace_id == ws,
        PartRevision.partmaster_partnumber == ci.partmaster_partnumber,
    ).order_by(PartRevision.version.desc()).first()
    if not rev:
        return None
    return rev.version


def _bl_summary_dict(b: ProductBaseline, db: Session) -> dict:
    """构建基线列表摘要（含 hasObsoletePartRevisions + configurationItemLatestRevision）。"""
    ws = b.configurationitem_workspace_id
    ci_id = b.configurationitem_id
    return {
        "id": b.id,
        "name": b.name,
        "type": _type_name(b.type),
        "configurationItemId": ci_id,
        "author": _get_user(db, b.author_login or "", ws),
        "creationDate": b.creation_date.isoformat() + "Z" if b.creation_date else None,
        "description": b.description or "",
        "hasObsoletePartRevisions": _has_obsolete_parts(db, b.partcollection_id),
        "configurationItemLatestRevision": _ci_latest_revision(
            db, ws, ci_id
        ),
        "baselinedParts": _query_baselined_parts(db, b.partcollection_id) if b.partcollection_id else [],
        "substituteLinks": _baseline_substitute_paths(db, b.id),
        "optionalUsageLinks": _baseline_optional_paths(db, b.id),
        "pathToPathLinks": _query_path_to_path_links(db, ws, ci_id, b.id),
        "optionalsParts": _decode_paths_to_part_links(db, ws, ci_id, _baseline_optional_paths(db, b.id)),
    }


def _bl_detail_dict(bl: ProductBaseline, db: Session) -> dict:
    """构建基线详情（完整字段，含 substitutesParts + optionalsParts）。"""
    ws = bl.configurationitem_workspace_id
    ci_id = bl.configurationitem_id
    return {
        "id": bl.id,
        "name": bl.name,
        "type": _type_name(bl.type),
        "configurationItemId": ci_id,
        "creationDate": bl.creation_date.isoformat() + "Z" if bl.creation_date else None,
        "description": bl.description or "",
        "author": _get_user(db, bl.author_login or "", ws),
        "hasObsoletePartRevisions": _has_obsolete_parts(db, bl.partcollection_id),
        "configurationItemLatestRevision": _ci_latest_revision(db, ws, ci_id),
        "baselinedParts": _query_baselined_parts(db, bl.partcollection_id),
        "substituteLinks": _baseline_substitute_paths(db, bl.id),
        "optionalUsageLinks": _baseline_optional_paths(db, bl.id),
        "pathToPathLinks": _query_path_to_path_links(db, ws, ci_id, bl.id),
        "substitutesParts": _decode_paths_to_part_links(db, ws, ci_id, _baseline_substitute_paths(db, bl.id)),
        "optionalsParts": _decode_paths_to_part_links(db, ws, ci_id, _baseline_optional_paths(db, bl.id)),
    }


# ── product-baselines（前端实际使用的路径）──

@router.get("/workspaces/{ws}/product-baselines", response_model=List[ProductBaselineSummaryDTO])
@router.get("/workspaces/{ws}/product-baselines/", include_in_schema=False)
def ci_scoped_baselines_root(ws: str,
                             current_user: Account = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    all_bl = db.query(ProductBaseline).filter(
        ProductBaseline.configurationitem_workspace_id == ws
    ).all()
    return [_bl_summary_dict(b, db) for b in all_bl]


@router.post("/workspaces/{ws}/product-baselines", status_code=201)
def create_workspace_baseline(ws: str, body: dict,
                              dryRun: bool = Query(False),
                              current_user: Account = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    """workspace 级创建基线，CI ID 从请求体获取（对应 Java POST /workspaces/{ws}/product-baselines）。"""
    ci_id = body.get("configurationItemId", "")
    raw_type = body.get("type", 0)
    if isinstance(raw_type, str):
        bl_type = _TYPE_MAP.get(raw_type.upper(), 0)
    else:
        bl_type = raw_type
    eff_date = _parse_iso_date(body.get("effectiveDate"))
    eff_serial = body.get("effectiveSerialNumber")
    eff_lot = body.get("effectiveLotId")
    if dryRun:
        return {"id": -1, "name": body.get("name", ""), "dryRun": True}
    bl = product_baseline_service.create_baseline(
        db, ws, ci_id, body.get("name", ""), bl_type,
        description=body.get("description", ""),
        effective_date=eff_date,
        effective_serial=eff_serial,
        effective_lot=eff_lot,
        baselined_parts=body.get("baselinedParts"),
        substitute_links=body.get("substituteLinks"),
        optional_usage_links=body.get("optionalUsageLinks"),
        user_login=current_user.login)
    return _bl_summary_dict(bl, db)


@router.get("/workspaces/{ws}/product-baselines/{ci_id}/baselines", response_model=List[ProductBaselineSummaryDTO])
@router.get("/workspaces/{ws}/product-baselines/{ci_id}/baselines/", include_in_schema=False)
def list_ci_baselines(ws: str, ci_id: str,
                      current_user: Account = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    return [_bl_summary_dict(b, db) for b in svc.list_baselines(db, ws, ci_id)]


@router.post("/workspaces/{ws}/product-baselines/{ci_id}/baselines", status_code=201)
@router.post("/workspaces/{ws}/product-baselines/{ci_id}/baselines/", status_code=201, include_in_schema=False)
def create_ci_scoped_baseline(ws: str, ci_id: str, body: dict,
                              dryRun: bool = Query(False),
                              current_user: Account = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    raw_type = body.get("type", 0)
    if isinstance(raw_type, str):
        bl_type = _TYPE_MAP.get(raw_type.upper(), 0)
    else:
        bl_type = raw_type
    eff_date = _parse_iso_date(body.get("effectiveDate"))
    eff_serial = body.get("effectiveSerialNumber")
    eff_lot = body.get("effectiveLotId")
    if dryRun:
        return {"id": -1, "name": body.get("name", ""), "dryRun": True}
    bl = product_baseline_service.create_baseline(
        db, ws, ci_id, body.get("name", ""), bl_type,
        description=body.get("description", ""),
        effective_date=eff_date,
        effective_serial=eff_serial,
        effective_lot=eff_lot,
        baselined_parts=body.get("baselinedParts"),
        substitute_links=body.get("substituteLinks"),
        optional_usage_links=body.get("optionalUsageLinks"),
        user_login=current_user.login)
    return _bl_summary_dict(bl, db)


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


def _query_baselined_parts(db: Session, partcollection_id: int | None) -> list:
    if partcollection_id is None:
        return []
    rows = db.execute(sql_text(
        "SELECT bp.target_partmaster_partnumber, bp.target_partrevision_version, bp.target_iteration "
        "FROM baselinedpart bp WHERE bp.partcollection_id = :pc_id"
    ), {"pc_id": partcollection_id}).fetchall()
    return [
        {"partNumber": r[0], "version": r[1], "iteration": r[2]}
        for r in rows
    ]


def _has_obsolete_parts(db: Session, partcollection_id: int | None) -> bool:
    if partcollection_id is None:
        return False
    row = db.execute(sql_text(
        "SELECT 1 FROM baselinedpart bp "
        "JOIN partrevision pr ON bp.target_workspace_id = pr.workspace_id "
        "AND bp.target_partmaster_partnumber = pr.partmaster_partnumber "
        "AND bp.target_partrevision_version = pr.version "
        "WHERE bp.partcollection_id = :pc_id AND pr.status = 2 LIMIT 1"
    ), {"pc_id": partcollection_id}).first()
    return row is not None


def _query_path_to_path_links(db: Session, ws: str, ci_id: str, baseline_id: int = None) -> list:
    """查询 PathToPathLink 列表。

    对齐 Java ProductBaselinesResource.getPathToPathLinkInProductBaseline：
    对每条 P2P link 分别 decode sourcePath/targetPath → LightPartLinkDTO 列表，
    填充 sourceComponents/targetComponents。

    若提供 baseline_id → 通过 productbaseline_p2plink 关联表查该基线的 links。
    否则返回空（工作区维度无直接关联，只有 CI 和 baseline 维度有关联）。
    """
    if baseline_id is None:
        return []
    rows = db.execute(sql_text(
        "SELECT ppl.id, ppl.type, ppl.sourcepath, ppl.targetpath, ppl.description "
        "FROM pathtopathlink ppl "
        "JOIN productbaseline_p2plink pbp ON pbp.pathtopathlink_id = ppl.id "
        "WHERE pbp.productbaseline_id = :bid"
    ), {"bid": baseline_id}).fetchall()
    result = []
    for r in rows:
        try:
            source_components = svc.decode_path(db, ws, ci_id, r[2])
        except Exception:
            source_components = []
        try:
            target_components = svc.decode_path(db, ws, ci_id, r[3])
        except Exception:
            target_components = []
        result.append({
            "id": r[0], "type": r[1], "sourcePath": r[2],
            "targetPath": r[3], "description": r[4],
            "sourceComponents": source_components,
            "targetComponents": target_components,
        })
    return result


def _decode_paths_to_part_links(db: Session, ws: str, ci_id: str, paths: list) -> list:
    """对齐 Java：对每个 path 字符串 decodePath → LightPartLinkListDTO{partLinks:[...]}。"""
    result = []
    for path in paths:
        if not path:
            continue
        try:
            part_links = svc.decode_path(db, ws, ci_id, path)
        except Exception:
            part_links = []
        result.append({"partLinks": part_links})
    return result


def _baseline_substitute_paths(db: Session, baseline_id: int) -> list:
    rows = db.execute(sql_text(
        "SELECT substitutelinks FROM productbaseline_substitutelink "
        "WHERE productbaseline_id = :bid"
    ), {"bid": baseline_id}).fetchall()
    return [r[0] for r in rows if r[0]]


def _baseline_optional_paths(db: Session, baseline_id: int) -> list:
    rows = db.execute(sql_text(
        "SELECT optionalusagelinks FROM productbaseline_optionallink "
        "WHERE productbaseline_id = :bid"
    ), {"bid": baseline_id}).fetchall()
    return [r[0] for r in rows if r[0]]


@router.get("/workspaces/{ws}/product-baselines/{ci_id}/baselines/{bl_id}", response_model=ProductBaselineDetailDTO)
@router.get("/workspaces/{ws}/product-baselines/{ci_id}/baselines/{bl_id}/", include_in_schema=False)
def get_ci_baseline_detail(ws: str, ci_id: str, bl_id: int,
                           current_user: Account = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    bl = db.query(ProductBaseline).filter(ProductBaseline.id == bl_id).first()
    if not bl:
        from app.core.exceptions import EntityNotFoundException
        raise EntityNotFoundException("BaselineNotFoundException", str(bl_id))
    return _bl_detail_dict(bl, db)


@router.delete("/workspaces/{ws}/product-baselines/{ci_id}/baselines/{bl_id}", status_code=204)
@router.delete("/workspaces/{ws}/product-baselines/{ci_id}/baselines/{bl_id}/", status_code=204, include_in_schema=False)
def delete_ci_baseline(ws: str, ci_id: str, bl_id: int,
                       current_user: Account = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    svc.delete_baseline(db, ws, bl_id)
    return {"status": "deleted"}


# ── products/{ci_id}/baselines ──

@router.get("/workspaces/{ws}/products/{ci_id}/baselines", response_model=List[ProductBaselineSummaryDTO])
@router.get("/workspaces/{ws}/products/{ci_id}/baselines/", include_in_schema=False)
def list_baselines(ws: str, ci_id: str,
                   current_user: Account = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    return [_bl_summary_dict(b, db) for b in svc.list_baselines(db, ws, ci_id)]


@router.get("/workspaces/{ws}/products/{ci_id}/baselines/{bl_id}", response_model=ProductBaselineDetailDTO)
@router.get("/workspaces/{ws}/products/{ci_id}/baselines/{bl_id}/", include_in_schema=False)
def get_baseline(ws: str, ci_id: str, bl_id: int,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    bl = db.query(ProductBaseline).filter(ProductBaseline.id == bl_id).first()
    if not bl:
        from app.core.exceptions import EntityNotFoundException
        raise EntityNotFoundException("BaselineNotFoundException", str(bl_id))
    return _bl_detail_dict(bl, db)


@router.post("/workspaces/{ws}/products/{ci_id}/baselines", status_code=201)
@router.post("/workspaces/{ws}/products/{ci_id}/baselines/", status_code=201, include_in_schema=False)
def create_baseline(ws: str, ci_id: str, body: dict,
                    dryRun: bool = Query(False),
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    raw_type = body.get("type", 0)
    if isinstance(raw_type, str):
        bl_type = _TYPE_MAP.get(raw_type.upper(), 0)
    else:
        bl_type = raw_type
    eff_date = _parse_iso_date(body.get("effectiveDate"))
    eff_serial = body.get("effectiveSerialNumber")
    eff_lot = body.get("effectiveLotId")
    if dryRun:
        return {"id": -1, "name": body.get("name", ""), "dryRun": True}
    bl = product_baseline_service.create_baseline(
        db, ws, ci_id, body.get("name", ""), bl_type,
        description=body.get("description", ""),
        effective_date=eff_date,
        effective_serial=eff_serial,
        effective_lot=eff_lot,
        baselined_parts=body.get("baselinedParts"),
        substitute_links=body.get("substituteLinks"),
        optional_usage_links=body.get("optionalUsageLinks"),
        user_login=current_user.login)
    return _bl_summary_dict(bl, db)


@router.delete("/workspaces/{ws}/products/{ci_id}/baselines/{bl_id}", status_code=204)
@router.delete("/workspaces/{ws}/products/{ci_id}/baselines/{bl_id}/", status_code=204, include_in_schema=False)
def delete_baseline(ws: str, ci_id: str, bl_id: int,
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    svc.delete_baseline(db, ws, bl_id)
    return {"status": "deleted"}


# ── baseline path-to-path-links ──

@router.get("/workspaces/{ws}/product-baselines/{pid}/baselines/{bid}/path-to-path-links-types")
@router.get("/workspaces/{ws}/product-baselines/{pid}/baselines/{bid}/path-to-path-links-types/", include_in_schema=False)
def baseline_path_to_path_links_types(ws: str, pid: str, bid: int,
                                       current_user: Account = Depends(get_current_user),
                                       db: Session = Depends(get_db)):
    """获取产品基线的 PathToPathLink 类型列表。"""
    links = _query_path_to_path_links(db, ws, pid, bid)
    types = {lk["type"] for lk in links if lk.get("type")}
    return [{"type": t} for t in types]


@router.get("/workspaces/{ws}/product-baselines/{pid}/baselines/{bid}/path-to-path-links/source/{source}/target/{target}")
@router.get("/workspaces/{ws}/product-baselines/{pid}/baselines/{bid}/path-to-path-links/source/{source}/target/{target}/", include_in_schema=False)
def baseline_path_to_path_links_detail(ws: str, pid: str, bid: int,
                                        source: str, target: str,
                                        current_user: Account = Depends(get_current_user),
                                        db: Session = Depends(get_db)):
    """获取产品基线的 PathToPathLink（按 source/target 筛选）。"""
    links = _query_path_to_path_links(db, ws, pid, bid)
    return [
        lk for lk in links
        if lk.get("sourcePath") == source and lk.get("targetPath") == target
    ]


# ── product-baselines/{id} direct endpoints ──
# 注意：light 版本通过 ?light=true 查询参数获取，不需要独立的 -light 后缀端点。
# Java ProductBaselinesResource 仅使用 @QueryParam("light")，无 -light 后缀路径。

@router.get("/workspaces/{ws}/product-baselines/{bl_id}", response_model=ProductBaselineDetailDTO)
@router.get("/workspaces/{ws}/product-baselines/{bl_id}/", include_in_schema=False)
def get_baseline_by_id(ws: str, bl_id: int,
                       light: bool = Query(False),
                       current_user: Account = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    bl = db.query(ProductBaseline).filter(ProductBaseline.id == bl_id).first()
    if not bl:
        from app.core.exceptions import EntityNotFoundException
        raise EntityNotFoundException("BaselineNotFoundException", str(bl_id))
    if light:
        return {
            "id": bl.id, "name": bl.name, "type": _type_name(bl.type),
            "configurationItemId": bl.configurationitem_id,
            "creationDate": bl.creation_date.isoformat() + "Z" if bl.creation_date else None,
            "description": bl.description or "",
            "author": _get_user(db, bl.author_login or "", bl.configurationitem_workspace_id),
        }
    return _bl_detail_dict(bl, db)


@router.get("/workspaces/{ws}/product-baselines/{bl_id}/export-files")
@router.get("/workspaces/{ws}/product-baselines/{bl_id}/export-files/", include_in_schema=False)
def baseline_export_files(ws: str, bl_id: int,
                           current_user: Account = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    """返回基线中所有零件的文件列表（nativeCAD + 附件）。

    对齐 Java ProductBaselineManagerBean.getBinaryResourceFromBaseline()。
    """
    from sqlalchemy import text
    rows = db.execute(text(
        """
        SELECT DISTINCT br.fullname
        FROM baselinedpart bp
        JOIN partiteration pi ON (
            pi.workspace_id = bp.target_workspace_id
            AND pi.partmaster_partnumber = bp.target_partmaster_partnumber
            AND pi.partrevision_version = bp.target_partrevision_version
            AND pi.iteration = bp.target_iteration
        )
        JOIN binaryresource br ON (
            br.fullname = pi.nativecadfile_fullname
        )
        WHERE bp.partcollection_id = (
            SELECT partcollection_id FROM productbaseline WHERE id = :bl_id
        )
        AND pi.nativecadfile_fullname IS NOT NULL
        """
    ), {"bl_id": bl_id}).fetchall()
    return [{"fullName": r[0]} for r in rows]


@router.get("/workspaces/{ws}/product-baselines/{ci_id}/baselines/{bl_id}/parts")
@router.get("/workspaces/{ws}/product-baselines/{ci_id}/baselines/{bl_id}/parts/", include_in_schema=False)
def baseline_parts(ws: str, ci_id: str, bl_id: int,
                   q: str = Query(None),
                   current_user: Account = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """返回基线中的零件列表（含关键字搜索，最多8条）。

    对齐 Java ProductBaselinesResource.getProductBaselineParts → getBaselinedPartWithReference。
    """
    base_sql = (
        "SELECT bp.target_partmaster_partnumber, bp.target_partrevision_version, "
        "bp.target_iteration, pm.name "
        "FROM baselinedpart bp "
        "JOIN partmaster pm ON pm.workspace_id = bp.target_workspace_id "
        "AND pm.partnumber = bp.target_partmaster_partnumber "
        "WHERE bp.partcollection_id = ("
        "  SELECT partcollection_id FROM productbaseline WHERE id = :bid"
        ")"
    )
    params = {"bid": bl_id}
    if q:
        base_sql += " AND bp.target_partmaster_partnumber ILIKE :q"
        params["q"] = f"%{q}%"
    base_sql += " ORDER BY bp.target_partmaster_partnumber LIMIT 8"
    rows = db.execute(sql_text(base_sql), params).fetchall()
    return [
        {"partNumber": r[0], "version": r[1], "iteration": r[2], "name": r[3] or r[0]}
        for r in rows
    ]
