"""零件集合路由（PartsResource）。"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.models.part import PartRevision, PartIteration, part_revision_tags
from app.schemas.part import (
    PartRevisionDTO, PartCreationDTO, CountDTO, LightPartMasterDTO,
)
from app.services.product_manager import ProductService
from app.services.part_mapper import map_revision

router = APIRouter()
svc = ProductService()


@router.get("/workspaces/{workspace_id}/parts", response_model=list[PartRevisionDTO])
def list_parts(
    workspace_id: str,
    start: int = Query(0, ge=0),
    length: int = Query(50, ge=1, le=500),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    revisions = svc.list_revisions(db, workspace_id, start, length)
    return [map_revision(pr, db) for pr in revisions]


@router.get("/workspaces/{workspace_id}/parts/count", response_model=CountDTO)
def count_parts(
    workspace_id: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CountDTO(count=svc.count_parts(db, workspace_id))


@router.get("/workspaces/{workspace_id}/parts/numbers",
             response_model=list[LightPartMasterDTO])
def search_numbers(
    workspace_id: str,
    q: str = Query(""),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    masters = svc.search_numbers(db, workspace_id, q)
    return [LightPartMasterDTO(partNumber=m.number, partName=m.name or "") for m in masters]


@router.get("/workspaces/{workspace_id}/parts/checkedout",
             response_model=list[PartRevisionDTO])
def list_checked_out(
    workspace_id: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    revisions = svc.list_checked_out(db, workspace_id)
    return [map_revision(pr, db) for pr in revisions]


@router.get("/workspaces/{workspace_id}/parts/countCheckedOut",
             response_model=CountDTO)
def count_checked_out(
    workspace_id: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CountDTO(count=len(svc.list_checked_out(db, workspace_id)))


@router.get("/workspaces/{workspace_id}/parts/search",
            response_model=list[PartRevisionDTO])
def search_parts(
    workspace_id: str,
    name: str = Query(None),
    number: str = Query(None),
    type: str = Query(None),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    revisions = svc.search_parts(db, workspace_id, name=name,
                                 number=number, type_=type)
    return [map_revision(pr, db) for pr in revisions]


@router.get("/workspaces/{workspace_id}/parts/tags/{tag_id}")
@router.get("/workspaces/{workspace_id}/parts/tags/{tag_id}/", include_in_schema=False)
def get_parts_by_tag(workspace_id: str, tag_id: str,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    revisions = (
        db.query(PartRevision)
        .join(part_revision_tags,
              (PartRevision.workspace_id == part_revision_tags.c.partmaster_workspace_id)
              & (PartRevision.partmaster_partnumber == part_revision_tags.c.partmaster_partnumber)
              & (PartRevision.version == part_revision_tags.c.partrevision_version))
        .filter(part_revision_tags.c.tag_label == tag_id,
                PartRevision.workspace_id == workspace_id)
        .all()
    )
    return [map_revision(pr, db) for pr in revisions]


@router.get("/workspaces/{workspace_id}/parts/parts_last_iter")
@router.get("/workspaces/{workspace_id}/parts/parts_last_iter/", include_in_schema=False)
def parts_last_iter(workspace_id: str, q: str = Query(""),
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    subq = (
        db.query(
            PartIteration.workspace_id,
            PartIteration.partmaster_partnumber,
            PartIteration.partrevision_version,
            func.max(PartIteration.iteration).label("max_iter"),
        )
        .filter(PartIteration.workspace_id == workspace_id)
        .group_by(
            PartIteration.workspace_id,
            PartIteration.partmaster_partnumber,
            PartIteration.partrevision_version,
        )
        .subquery()
    )
    rows = (
        db.query(
            PartRevision,
            subq.c.max_iter,
        )
        .join(
            subq,
            (PartRevision.workspace_id == subq.c.workspace_id)
            & (PartRevision.partmaster_partnumber == subq.c.partmaster_partnumber)
            & (PartRevision.version == subq.c.partrevision_version),
        )
        .filter(PartRevision.workspace_id == workspace_id)
    )
    if q:
        rows = rows.filter(
            PartRevision.partmaster_partnumber.ilike(f"%{q}%")
        )
    result = []
    for pr, max_iter in rows.all():
        dto = map_revision(pr, db)
        result.append(dto.model_dump())
    return result


@router.post("/workspaces/{workspace_id}/parts",
            response_model=PartRevisionDTO, status_code=201)
@router.post("/workspaces/{workspace_id}/parts/",
            response_model=PartRevisionDTO, status_code=201, include_in_schema=False)
def create_part(
    workspace_id: str,
    body: PartCreationDTO,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pr = svc.create_part(db, workspace_id, current_user.login, body)
    return map_revision(pr, db)


# ── queries stubs ──────────────────────────────────────────────

@router.get("/workspaces/{workspace_id}/parts/queries")
@router.get("/workspaces/{workspace_id}/parts/queries/", include_in_schema=False)
def get_queries(workspace_id: str,
                current_user: Account = Depends(get_current_user),
                db: Session = Depends(get_db)):
    return []


@router.post("/workspaces/{workspace_id}/parts/queries")
@router.post("/workspaces/{workspace_id}/parts/queries/", include_in_schema=False)
def post_workspace_query(workspace_id: str,
                         body: dict = Body(...),
                         current_user: Account = Depends(get_current_user)):
    return []


@router.post("/parts/queries")
@router.post("/parts/queries/", include_in_schema=False)
def post_queries(body: dict = Body(...),
                 current_user: Account = Depends(get_current_user)):
    return []


@router.delete("/parts/queries/{query_id}", status_code=204)
@router.delete("/parts/queries/{query_id}/", status_code=204, include_in_schema=False)
def delete_query(query_id: str,
                 current_user: Account = Depends(get_current_user)):
    return Response(status_code=204)


@router.get("/parts/query-export")
@router.get("/parts/query-export/", include_in_schema=False)
def query_export(current_user: Account = Depends(get_current_user)):
    return {}


# ── imports ────────────────────────────────────────────────────

@router.get("/workspaces/{workspace_id}/parts/imports/{filename}")
@router.get("/workspaces/{workspace_id}/parts/imports/{filename}/", include_in_schema=False)
def imports_get(workspace_id: str, filename: str,
                current_user: Account = Depends(get_current_user)):
    return {}


@router.get("/workspaces/{workspace_id}/parts/import/{import_id}")
@router.get("/workspaces/{workspace_id}/parts/import/{import_id}/", include_in_schema=False)
def import_get(workspace_id: str, import_id: str,
               current_user: Account = Depends(get_current_user)):
    return {}


@router.post("/parts/import", status_code=201)
@router.post("/parts/import/", status_code=201, include_in_schema=False)
def post_import(body: dict = Body(...),
                current_user: Account = Depends(get_current_user)):
    import_id = f"import-{uuid.uuid4().hex[:12]}"
    return {"id": import_id}


@router.post("/parts/importPreview", status_code=201)
@router.post("/parts/importPreview/", status_code=201, include_in_schema=False)
def post_import_preview(body: dict = Body(...),
                        current_user: Account = Depends(get_current_user)):
    import_id = f"import-{uuid.uuid4().hex[:12]}"
    return {"id": import_id}


@router.delete("/parts/import/{import_id}", status_code=204)
@router.delete("/parts/import/{import_id}/", status_code=204, include_in_schema=False)
def delete_import(import_id: str,
                  current_user: Account = Depends(get_current_user)):
    return Response(status_code=204)
