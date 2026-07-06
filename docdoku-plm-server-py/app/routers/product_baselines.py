"""产品基线（ProductBaseline）端点路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.product_structure import ProductStructureService

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
svc = ProductStructureService()


# ── product-baselines（前端实际使用的路径）──

@router.get("/workspaces/{ws}/product-baselines")
@router.get("/workspaces/{ws}/product-baselines/", include_in_schema=False)
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
@router.get("/workspaces/{ws}/product-baselines/{ci_id}/baselines/", include_in_schema=False)
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
                               current_user.login, body.get("baselinedParts"))
    return {"id": bl.id, "name": bl.name}


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


@router.get("/workspaces/{ws}/product-baselines/{ci_id}/baselines/{bl_id}")
@router.get("/workspaces/{ws}/product-baselines/{ci_id}/baselines/{bl_id}/", include_in_schema=False)
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
            "baselinedParts": _query_baselined_parts(db, bl.partcollection_id),
            "substituteLinks": [], "optionalUsageLinks": [],
            "pathToPathLinks": []}


@router.delete("/workspaces/{ws}/product-baselines/{ci_id}/baselines/{bl_id}", status_code=204)
def delete_ci_baseline(ws: str, ci_id: str, bl_id: int,
                       current_user: Account = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    svc.delete_baseline(db, ws, bl_id)
    return {"status": "deleted"}


@router.get("/workspaces/{ws}/product-baselines/{bl_id}")
@router.get("/workspaces/{ws}/product-baselines/{bl_id}/", include_in_schema=False)
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


# ── products/{ci_id}/baselines ──

@router.get("/workspaces/{ws}/products/{ci_id}/baselines")
@router.get("/workspaces/{ws}/products/{ci_id}/baselines/", include_in_schema=False)
def list_baselines(ws: str, ci_id: str,
                   current_user: Account = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    return [{"id": b.id, "name": b.name, "type": b.type,
             "configurationItemId": b.configurationitem_id}
            for b in svc.list_baselines(db, ws, ci_id)]


@router.get("/workspaces/{ws}/products/{ci_id}/baselines/{bl_id}")
@router.get("/workspaces/{ws}/products/{ci_id}/baselines/{bl_id}/", include_in_schema=False)
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
            "baselinedParts": _query_baselined_parts(db, bl.partcollection_id),
            "substituteLinks": [], "optionalUsageLinks": [],
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
                               current_user.login, body.get("baselinedParts"))
    return {"id": bl.id, "name": bl.name}


@router.delete("/workspaces/{ws}/products/{ci_id}/baselines/{bl_id}")
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
