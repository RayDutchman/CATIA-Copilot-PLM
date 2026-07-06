"""产品基线（ProductBaseline）端点路由。"""
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
from app.schemas.product import ProductBaselineSummaryDTO, ProductBaselineDetailDTO

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
svc = ProductStructureService()


def _ci_latest_revision(db: Session, ws: str, ci_id: str) -> dict | None:
    """查询 CI 的根零件最新版本信息。"""
    ci = db.query(ConfigurationItem).filter(
        ConfigurationItem.workspace_id == ws,
        ConfigurationItem.id == ci_id,
    ).first()
    if not ci or not ci.partmaster_partnumber:
        return None
    rev = db.query(PartRevision).filter(
        PartRevision.workspace_id == ws,
        PartRevision.partmaster_partnumber == ci.partmaster_partnumber,
    ).order_by(PartRevision.creation_date.desc()).first()
    if not rev:
        return None
    return {
        "partNumber": rev.partmaster_partnumber,
        "version": rev.version,
        "status": rev.status if rev.status is not None else 0,
    }


def _bl_summary_dict(b: ProductBaseline, db: Session) -> dict:
    """构建基线列表摘要（含 hasObsoletePartRevisions + configurationItemLatestRevision）。"""
    ws = b.configurationitem_workspace_id
    return {
        "id": b.id,
        "name": b.name,
        "type": b.type,
        "configurationItemId": b.configurationitem_id,
        "author": _get_user(db, b.author_login or "", ws),
        "creationDate": b.creation_date.isoformat() + "Z" if b.creation_date else None,
        "description": b.description or "",
        "hasObsoletePartRevisions": _has_obsolete_parts(db, b.partcollection_id),
        "configurationItemLatestRevision": _ci_latest_revision(
            db, ws, b.configurationitem_id
        ),
        "baselinedParts": _query_baselined_parts(db, b.partcollection_id) if b.partcollection_id else [],
        "substituteLinks": _query_substitute_links(db, ws, b.partcollection_id),
        "optionalUsageLinks": _query_optional_links(db, ws, b.partcollection_id),
        "pathToPathLinks": _query_path_to_path_links(db, ws),
        "substitutesParts": [],
        "optionalsParts": [],
    }


def _bl_detail_dict(bl: ProductBaseline, db: Session) -> dict:
    """构建基线详情（完整字段，含 substitutesParts + optionalsParts）。"""
    ws = bl.configurationitem_workspace_id
    return {
        "id": bl.id,
        "name": bl.name,
        "type": bl.type,
        "configurationItemId": bl.configurationitem_id,
        "configurationItemWorkspaceId": ws,
        "creationDate": bl.creation_date.isoformat() + "Z" if bl.creation_date else None,
        "description": bl.description or "",
        "author": _get_user(db, bl.author_login or "", ws),
        "baselinedParts": _query_baselined_parts(db, bl.partcollection_id),
        "substituteLinks": _query_substitute_links(db, ws, bl.partcollection_id),
        "optionalUsageLinks": _query_optional_links(db, ws, bl.partcollection_id),
        "pathToPathLinks": _query_path_to_path_links(db, ws),
        "substitutesParts": [],
        "optionalsParts": [],
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
    bl_type = body.get("type", 0)
    if isinstance(bl_type, str):
        bl_type = 0 if bl_type.upper() == "LATEST" else 1
    if dryRun:
        return {"id": -1, "name": body.get("name", ""), "dryRun": True}
    bl = svc.create_baseline(db, ws, ci_id, body.get("name", ""),
                               body.get("description", ""), bl_type,
                               current_user.login, body.get("baselinedParts"),
                               body.get("substituteLinks"),
                               body.get("optionalUsageLinks"))
    return {"id": bl.id, "name": bl.name}


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
    bl_type = body.get("type", 0)
    if isinstance(bl_type, str):
        bl_type = 0 if bl_type.upper() == "LATEST" else 1
    if dryRun:
        return {"id": -1, "name": body.get("name", ""), "dryRun": True}
    bl = svc.create_baseline(db, ws, ci_id, body.get("name", ""),
                               body.get("description", ""), bl_type,
                               current_user.login, body.get("baselinedParts"),
                               body.get("substituteLinks"),
                               body.get("optionalUsageLinks"))
    return {"id": bl.id, "name": bl.name}


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


def _query_path_to_path_links(db: Session, ws: str) -> list:
    rows = db.execute(sql_text(
        "SELECT id, type, name, sourcepath, targetpath, description "
        "FROM pathtopathlink WHERE workspace_id = :ws"
    ), {"ws": ws}).fetchall()
    return [{"id": r[0], "type": r[1], "name": r[2],
             "sourcePath": r[3], "targetPath": r[4], "description": r[5]}
            for r in rows]


def _query_substitute_links(db: Session, ws: str, partcollection_id: int | None) -> list:
    if partcollection_id is None:
        return []
    rows = db.execute(sql_text(
        "SELECT DISTINCT psl.substitute_partnumber, pm.name "
        "FROM partsubstitutelink psl "
        "JOIN baselinedpart bp ON bp.target_workspace_id = psl.component_workspace_id "
        "AND bp.target_partmaster_partnumber = psl.component_partnumber "
        "AND bp.target_partrevision_version = psl.component_partversion "
        "LEFT JOIN partmaster pm ON pm.workspace_id = psl.substitute_workspace_id "
        "AND pm.number = psl.substitute_partnumber "
        "WHERE bp.partcollection_id = :pc_id"
    ), {"pc_id": partcollection_id}).fetchall()
    return [{"partNumber": r[0], "name": r[1] or r[0]} for r in rows]


def _query_optional_links(db: Session, ws: str, partcollection_id: int | None) -> list:
    if partcollection_id is None:
        return []
    rows = db.execute(sql_text(
        "SELECT DISTINCT pul.component_partnumber "
        "FROM partusagelink pul "
        "JOIN baselinedpart bp ON bp.target_workspace_id = pul.component_workspace_id "
        "AND bp.target_partmaster_partnumber = pul.component_partnumber "
        "AND bp.target_partrevision_version = pul.component_partversion "
        "WHERE bp.partcollection_id = :pc_id AND pul.optional = true"
    ), {"pc_id": partcollection_id}).fetchall()
    return [{"partNumber": r[0]} for r in rows]


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
    bl_type = body.get("type", 0)
    if isinstance(bl_type, str):
        bl_type = 0 if bl_type.upper() == "LATEST" else 1
    if dryRun:
        return {"id": -1, "name": body.get("name", ""), "dryRun": True}
    bl = svc.create_baseline(db, ws, ci_id, body.get("name", ""),
                               body.get("description", ""), bl_type,
                               current_user.login, body.get("baselinedParts"),
                               body.get("substituteLinks"),
                               body.get("optionalUsageLinks"))
    return {"id": bl.id, "name": bl.name}


@router.delete("/workspaces/{ws}/products/{ci_id}/baselines/{bl_id}")
@router.delete("/workspaces/{ws}/products/{ci_id}/baselines/{bl_id}/", include_in_schema=False)
def delete_baseline(ws: str, ci_id: str, bl_id: int,
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    svc.delete_baseline(db, ws, bl_id)
    return {"status": "deleted"}


# ── baseline path-to-path-links ──

@router.get("/workspaces/{ws}/product-baselines/{pid}/baselines/{bid}/path-to-path-links-types")
@router.get("/workspaces/{ws}/product-baselines/{pid}/baselines/{bid}/path-to-path-links-types/", include_in_schema=False)
def baseline_path_to_path_links_types(ws: str, pid: str, bid: int,
                                       current_user: Account = Depends(get_current_user)):
    return []


@router.get("/workspaces/{ws}/product-baselines/{pid}/baselines/{bid}/path-to-path-links/source/{source}/target/{target}")
@router.get("/workspaces/{ws}/product-baselines/{pid}/baselines/{bid}/path-to-path-links/source/{source}/target/{target}/", include_in_schema=False)
def baseline_path_to_path_links_detail(ws: str, pid: str, bid: int,
                                        source: str, target: str,
                                        current_user: Account = Depends(get_current_user)):
    return {}


# ── product-baselines/{id} direct endpoints ──

@router.get("/workspaces/{ws}/product-baselines/{bl_id}", response_model=ProductBaselineDetailDTO)
@router.get("/workspaces/{ws}/product-baselines/{bl_id}/", include_in_schema=False)
def get_baseline_by_id(ws: str, bl_id: int,
                       current_user: Account = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    bl = db.query(ProductBaseline).filter(ProductBaseline.id == bl_id).first()
    if not bl:
        from app.core.exceptions import EntityNotFoundException
        raise EntityNotFoundException("BaselineNotFoundException", str(bl_id))
    return _bl_detail_dict(bl, db)


@router.get("/workspaces/{ws}/product-baselines/{bl_id}-light")
@router.get("/workspaces/{ws}/product-baselines/{bl_id}-light/", include_in_schema=False)
def get_baseline_light(ws: str, bl_id: int,
                        current_user: Account = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    bl = db.query(ProductBaseline).filter(ProductBaseline.id == bl_id).first()
    if not bl:
        from app.core.exceptions import EntityNotFoundException
        raise EntityNotFoundException("BaselineNotFoundException", str(bl_id))
    return {
        "id": bl.id, "name": bl.name, "type": bl.type,
        "configurationItemId": bl.configurationitem_id,
        "creationDate": bl.creation_date.isoformat() + "Z" if bl.creation_date else None,
        "description": bl.description or "",
        "author": _get_user(db, bl.author_login or "", bl.configurationitem_workspace_id),
    }


@router.get("/workspaces/{ws}/product-baselines/{bl_id}/export-files")
@router.get("/workspaces/{ws}/product-baselines/{bl_id}/export-files/", include_in_schema=False)
def baseline_export_files(ws: str, bl_id: int,
                           current_user: Account = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    return []
