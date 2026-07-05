"""零件集合路由（与 Payara 路径完全一致）。"""
import re
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.models.part import PartRevision, PartIteration, Conversion, part_revision_tags
from app.schemas.part import (
    PartRevisionDTO, PartCreationDTO, PartIterationUpdateDTO,
    ConversionDTO, ConversionResultDTO, CountDTO, LightPartMasterDTO,
)
from app.services.product_service import ProductService
from app.services.part_mapper import map_revision
from app.services import conversion_service
from app.services.acl_helper import apply_acl
from app.services.workflow_service import workflow_service

router = APIRouter()
svc = ProductService()


def _split_part_key(part_key: str) -> tuple[str, str]:
    """从路径参数拆分零件号和版本（零件号可含 -，版本仅 [A-Z]+）。"""
    m = re.match(r'^(.+)-([A-Z]+)$', part_key)
    if not m:
        raise HTTPException(400, f"Invalid part key format: {part_key}")
    return m.group(1), m.group(2)


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


@router.get("/workspaces/{workspace_id}/part-templates")
@router.get("/workspaces/{workspace_id}/part-templates/", include_in_schema=False)
def list_part_templates(workspace_id: str,
                        current_user: Account = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    try:
        return []
    except Exception:
        return []


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


@router.get("/workspaces/{workspace_id}/parts/queries")
@router.get("/workspaces/{workspace_id}/parts/queries/", include_in_schema=False)
def get_queries(workspace_id: str,
                current_user: Account = Depends(get_current_user),
                db: Session = Depends(get_db)):
    return []


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


@router.get("/workspaces/{workspace_id}/parts/{part_number}/latest-revision",
             response_model=PartRevisionDTO)
def get_latest_revision(
    workspace_id: str,
    part_number: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pr = svc.get_latest_revision(db, workspace_id, part_number)
    return map_revision(pr, db)


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


@router.get("/workspaces/{workspace_id}/parts/{part_key}/used-by-as-component")
@router.get("/workspaces/{workspace_id}/parts/{part_key}/used-by-as-component/", include_in_schema=False)
def used_by_component(workspace_id: str, part_key: str,
                      current_user: Account = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    from sqlalchemy import text
    number, version = _split_part_key(part_key)
    rows = db.execute(text(
        "SELECT DISTINCT pr.workspace_id, pr.partmaster_partnumber, pr.version "
        "FROM partrevision pr "
        "JOIN partiteration pi ON pi.workspace_id = pr.workspace_id "
        "  AND pi.partmaster_partnumber = pr.partmaster_partnumber "
        "  AND pi.partrevision_version = pr.version "
        "JOIN partiteration_partusagelink piul "
        "  ON piul.workspace_id = pi.workspace_id "
        "  AND piul.partmaster_partnumber = pi.partmaster_partnumber "
        "  AND piul.partrevision_version = pi.partrevision_version "
        "  AND piul.iteration = pi.iteration "
        "JOIN partusagelink pul ON pul.id = piul.component_id "
        "WHERE pul.component_workspace_id = :ws AND pul.component_partnumber = :pn"
    ), {"ws": workspace_id, "pn": number}).fetchall()
    result = []
    for row in rows:
        pr = svc.get_revision(db, row.workspace_id, row.partmaster_partnumber,
                              row.version)
        result.append(map_revision(pr, db))
    return result


@router.get("/workspaces/{workspace_id}/parts/{part_key}/used-by-as-substitute")
@router.get("/workspaces/{workspace_id}/parts/{part_key}/used-by-as-substitute/", include_in_schema=False)
def used_by_substitute(workspace_id: str, part_key: str,
                       current_user: Account = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    from sqlalchemy import text
    number, version = _split_part_key(part_key)
    rows = db.execute(text(
        "SELECT DISTINCT pr.workspace_id, pr.partmaster_partnumber, pr.version "
        "FROM partrevision pr "
        "JOIN partiteration pi ON pi.workspace_id = pr.workspace_id "
        "  AND pi.partmaster_partnumber = pr.partmaster_partnumber "
        "  AND pi.partrevision_version = pr.version "
        "JOIN partiteration_partusagelink piul "
        "  ON piul.workspace_id = pi.workspace_id "
        "  AND piul.partmaster_partnumber = pi.partmaster_partnumber "
        "  AND piul.partrevision_version = pi.partrevision_version "
        "  AND piul.iteration = pi.iteration "
        "JOIN pusagelink_psubstitutelink upl ON upl.partusagelink_id = piul.component_id "
        "JOIN partsubstitutelink psl ON psl.id = upl.partsubstitute_id "
        "WHERE psl.substitute_workspace_id = :ws AND psl.substitute_partnumber = :pn"
    ), {"ws": workspace_id, "pn": number}).fetchall()
    result = []
    for row in rows:
        pr = svc.get_revision(db, row.workspace_id, row.partmaster_partnumber,
                              row.version)
        result.append(map_revision(pr, db))
    return result


@router.get("/workspaces/{workspace_id}/parts/{part_key}/instances")
@router.get("/workspaces/{workspace_id}/parts/{part_key}/instances/", include_in_schema=False)
def get_instances(workspace_id: str, part_key: str,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    return []


@router.get("/workspaces/{workspace_id}/parts/{part_key}/baselines")
@router.get("/workspaces/{workspace_id}/parts/{part_key}/baselines/", include_in_schema=False)
def get_baselines(workspace_id: str, part_key: str,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    return []


@router.get("/workspaces/{workspace_id}/parts/{part_key}/aborted-workflows")
@router.get("/workspaces/{workspace_id}/parts/{part_key}/aborted-workflows/", include_in_schema=False)
def get_aborted_workflows(workspace_id: str, part_key: str,
                          current_user: Account = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    return workflow_service.get_aborted_workflows_for_part(
        db, workspace_id, number, version)


@router.get("/workspaces/{workspace_id}/parts/{part_key}/used-by-product-instance-masters")
@router.get("/workspaces/{workspace_id}/parts/{part_key}/used-by-product-instance-masters/", include_in_schema=False)
def used_by_product(workspace_id: str, part_key: str,
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    return []


@router.get("/workspaces/{workspace_id}/parts/{part_key}",
            response_model=PartRevisionDTO)
def get_part_revision(
    workspace_id: str,
    part_key: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    number, version = _split_part_key(part_key)
    pr = svc.get_revision(db, workspace_id, number, version)
    return map_revision(pr, db)


@router.delete("/workspaces/{workspace_id}/parts/{part_key}",
               status_code=204)
def delete_part_revision(
    workspace_id: str,
    part_key: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    number, version = _split_part_key(part_key)
    svc.delete_revision(db, workspace_id, number, version, current_user.login)


@router.put("/workspaces/{workspace_id}/parts/{part_key}/checkout",
            response_model=PartRevisionDTO)
def checkout_part(
    workspace_id: str,
    part_key: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    number, version = _split_part_key(part_key)
    pr = svc.checkout(db, workspace_id, number, version, current_user.login)
    return map_revision(pr, db)


@router.put("/workspaces/{workspace_id}/parts/{part_key}/checkin",
            response_model=PartRevisionDTO)
def checkin_part(
    workspace_id: str,
    part_key: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    number, version = _split_part_key(part_key)
    pr = svc.checkin(db, workspace_id, number, version, current_user.login)
    return map_revision(pr, db)


@router.put("/workspaces/{workspace_id}/parts/{part_key}/undocheckout",
            response_model=PartRevisionDTO)
def undo_checkout_part(
    workspace_id: str,
    part_key: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    number, version = _split_part_key(part_key)
    pr = svc.undo_checkout(db, workspace_id, number, version, current_user.login)
    return map_revision(pr, db)


@router.put("/workspaces/{workspace_id}/parts/{part_key}/iterations/{iteration}",
            response_model=PartRevisionDTO)
def update_iteration(
    workspace_id: str,
    part_key: str,
    iteration: int,
    body: PartIterationUpdateDTO,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    number, version = _split_part_key(part_key)
    pr = svc.update_iteration(db, workspace_id, number, version,
                               iteration, current_user.login, body)
    return map_revision(pr, db)


@router.get(
    "/workspaces/{workspace_id}/parts/{part_key}/iterations/{iteration}/conversion",
    response_model=ConversionDTO,
)
def get_conversion_status(
    workspace_id: str,
    part_key: str,
    iteration: int,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    number, version = _split_part_key(part_key)
    conv = svc.get_conversion(db, workspace_id, number, version, iteration)
    if conv is None:
        return Response(status_code=204)
    return ConversionDTO(
        pending=conv.pending or False,
        succeed=conv.succeed or False,
        startDate=conv.start_date,
        endDate=conv.end_date,
    )


@router.put("/workspaces/{workspace_id}/parts/{part_key}/conversion")
def conversion_callback(
    workspace_id: str,
    part_key: str,
    body: ConversionResultDTO,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    number, version = _split_part_key(part_key)
    conversion_service.handle_callback(db, workspace_id, number, version, body)
    db.commit()
    return {"status": "ok"}


@router.put("/workspaces/{workspace_id}/parts/{part_key}/release",
            response_model=PartRevisionDTO)
def release_part(workspace_id: str, part_key: str,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    pr = svc.release(db, workspace_id, number, version, current_user.login)
    return map_revision(pr, db)


@router.put("/workspaces/{workspace_id}/parts/{part_key}/obsolete",
            response_model=PartRevisionDTO)
def obsolete_part(workspace_id: str, part_key: str,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    pr = svc.mark_obsolete(db, workspace_id, number, version, current_user.login)
    return map_revision(pr, db)


@router.put("/workspaces/{workspace_id}/parts/{part_key}/newVersion",
            response_model=PartRevisionDTO)
def new_version_part(workspace_id: str, part_key: str,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    pr = svc.create_new_version(db, workspace_id, number, version, current_user.login)
    return map_revision(pr, db)


@router.put("/workspaces/{workspace_id}/parts/{part_key}/tags",
            response_model=PartRevisionDTO)
def set_tags(workspace_id: str, part_key: str,
             body: dict = Body(...),
             current_user: Account = Depends(get_current_user),
             db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    pr = svc.set_tags(db, workspace_id, number, version, body.get("tags", []))
    return map_revision(pr, db)


@router.post("/workspaces/{workspace_id}/parts/{part_key}/tags",
             response_model=PartRevisionDTO)
def add_tag(workspace_id: str, part_key: str,
            body: dict = Body(...),
            current_user: Account = Depends(get_current_user),
            db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    pr = svc.add_tag(db, workspace_id, number, version, body.get("tag", ""))
    return map_revision(pr, db)


@router.delete("/workspaces/{workspace_id}/parts/{part_key}/tags/{tag_label}",
               response_model=PartRevisionDTO)
def remove_tag(workspace_id: str, part_key: str, tag_label: str,
               current_user: Account = Depends(get_current_user),
               db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    pr = svc.remove_tag(db, workspace_id, number, version, tag_label)
    return map_revision(pr, db)


@router.get("/workspaces/{workspace_id}/parts/{part_key}/tags")
@router.get("/workspaces/{workspace_id}/parts/{part_key}/tags/", include_in_schema=False)
def get_tags(workspace_id: str, part_key: str,
             current_user: Account = Depends(get_current_user),
             db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    pr = svc.get_revision(db, workspace_id, number, version)
    return [t.label for t in (pr.tags or [])]


# ── share / publish / unpublish ────────────────────────────────

@router.post("/workspaces/{workspace_id}/parts/{part_key}/share")
@router.post("/workspaces/{workspace_id}/parts/{part_key}/share/", include_in_schema=False)
def share_part(workspace_id: str, part_key: str,
               current_user: Account = Depends(get_current_user),
               db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    pr = svc.get_revision(db, workspace_id, number, version)
    return map_revision(pr, db)


@router.put("/workspaces/{workspace_id}/parts/{part_key}/publish")
@router.put("/workspaces/{workspace_id}/parts/{part_key}/publish/", include_in_schema=False)
def publish_part(workspace_id: str, part_key: str,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    pr = svc.get_revision(db, workspace_id, number, version)
    pr.public_shared = True
    db.commit()
    return map_revision(pr, db)


@router.put("/workspaces/{workspace_id}/parts/{part_key}/unpublish")
@router.put("/workspaces/{workspace_id}/parts/{part_key}/unpublish/", include_in_schema=False)
def unpublish_part(workspace_id: str, part_key: str,
                   current_user: Account = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    pr = svc.get_revision(db, workspace_id, number, version)
    pr.public_shared = False
    db.commit()
    return map_revision(pr, db)


# ── queries stubs ──────────────────────────────────────────────

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


# ── imports stubs ──────────────────────────────────────────────

@router.post("/parts/import", status_code=201)
@router.post("/parts/import/", status_code=201, include_in_schema=False)
def post_import(body: dict = Body(...),
                current_user: Account = Depends(get_current_user)):
    return {}


@router.delete("/parts/import/{import_id}", status_code=204)
@router.delete("/parts/import/{import_id}/", status_code=204, include_in_schema=False)
def delete_import(import_id: str,
                  current_user: Account = Depends(get_current_user)):
    return Response(status_code=204)


# ── filter by baseline ─────────────────────────────────────────

@router.get("/workspaces/{workspace_id}/parts/{pn}/filter/{baseline_id}")
@router.get("/workspaces/{workspace_id}/parts/{pn}/filter/{baseline_id}/", include_in_schema=False)
def filter_by_baseline(workspace_id: str, pn: str, baseline_id: str,
                       current_user: Account = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    return []


# ── retry conversion ───────────────────────────────────────────

@router.put("/workspaces/{workspace_id}/parts/{part_key}/iterations/{iteration}/conversion")
@router.put("/workspaces/{workspace_id}/parts/{part_key}/iterations/{iteration}/conversion/", include_in_schema=False)
def retry_conversion(workspace_id: str, part_key: str, iteration: int,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    conv = svc.get_conversion(db, workspace_id, number, version, iteration)
    if conv is None:
        conv = svc.create_conversion(db, workspace_id, number, version, iteration)
    else:
        conv.pending = True
        conv.succeed = False
        conv.start_date = None
        conv.end_date = None
    db.commit()
    return {"status": "retry_queued"}


# ── ACL ────────────────────────────────────────────────────────


@router.put("/workspaces/{workspace_id}/parts/{part_key}/acl")
@router.put("/workspaces/{workspace_id}/parts/{part_key}/acl/", include_in_schema=False)
def update_part_acl(workspace_id: str, part_key: str, body: dict,
                    db: Session = Depends(get_db),
                    current_user: Account = Depends(get_current_user)):
    number, version = _split_part_key(part_key)
    pr = svc.get_revision(db, workspace_id, number, version)
    acl_id = getattr(pr, "acl_id", None)
    user_entries = body.get("userEntries", {})
    group_entries = body.get("groupEntries", {})
    new_acl_id = apply_acl(db, acl_id, user_entries, group_entries)
    if pr.acl_id != new_acl_id:
        pr.acl_id = new_acl_id
        db.commit()
    return {"aclId": new_acl_id}

