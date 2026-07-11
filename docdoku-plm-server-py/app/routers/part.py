"""单个零件 CRUD（PartResource）。"""
import re
import uuid
import hashlib
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import PartIterationNotFoundException
from app.models.auth import Account
from app.models.part import SharedEntity
from app.models.product.part_iteration import PartIteration
from app.schemas.part import PartRevisionDTO, PartIterationUpdateDTO, ConversionDTO, ConversionResultDTO, StatusDTO, SharedPartDTO, AclIdDTO
from app.schemas.workflow import WorkflowAbortedDTO
from app.services.product_manager import ProductService
from app.services.part_mapper import map_revision
from app.services import converter
from app.services.factory.acl_factory import apply_acl
from app.services.workflow_manager import workflow_service
from app.services.file_export.instance_body_writer_tools import (
    identity_matrix, collect_leaf_instances,
)

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
svc = ProductService()


def _split_part_key(part_key: str) -> tuple[str, str]:
    m = re.match(r'^(.+)-([A-Z]+)$', part_key)
    if not m:
        raise HTTPException(400, f"Invalid part key format: {part_key}")
    return m.group(1), m.group(2)


@router.get("/workspaces/{workspace_id}/parts/{part_key}",
            response_model=PartRevisionDTO)
def get_part_revision(
    workspace_id: str,
    part_key: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    number, version = _split_part_key(part_key)
    pr = svc.get_revision(db, workspace_id, number, version,
                          current_user_login=current_user.login)
    return map_revision(pr, db)

@router.delete("/workspaces/{workspace_id}/parts/{part_key}", status_code=204)
@router.delete("/workspaces/{workspace_id}/parts/{part_key}/", status_code=204, include_in_schema=False)
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
@router.put("/workspaces/{workspace_id}/parts/{part_key}/checkout/",
            response_model=PartRevisionDTO, include_in_schema=False)
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
@router.put("/workspaces/{workspace_id}/parts/{part_key}/checkin/",
            response_model=PartRevisionDTO, include_in_schema=False)
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
@router.put("/workspaces/{workspace_id}/parts/{part_key}/undocheckout/",
            response_model=PartRevisionDTO, include_in_schema=False)
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
@router.put("/workspaces/{workspace_id}/parts/{part_key}/iterations/{iteration}/",
            response_model=PartRevisionDTO, include_in_schema=False)
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


@router.put("/workspaces/{workspace_id}/parts/{part_key}/conversion",
             response_model=StatusDTO)
@router.put("/workspaces/{workspace_id}/parts/{part_key}/conversion/",
            response_model=StatusDTO, include_in_schema=False)
def conversion_callback(
    workspace_id: str,
    part_key: str,
    body: ConversionResultDTO,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    number, version = _split_part_key(part_key)
    converter.handle_callback(db, workspace_id, number, version, body)
    db.commit()
    return {"status": "ok"}


@router.put("/workspaces/{workspace_id}/parts/{part_key}/release",
            response_model=PartRevisionDTO)
@router.put("/workspaces/{workspace_id}/parts/{part_key}/release/",
            response_model=PartRevisionDTO, include_in_schema=False)
def release_part(workspace_id: str, part_key: str,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    pr = svc.release(db, workspace_id, number, version, current_user.login)
    return map_revision(pr, db)


@router.put("/workspaces/{workspace_id}/parts/{part_key}/obsolete",
            response_model=PartRevisionDTO)
@router.put("/workspaces/{workspace_id}/parts/{part_key}/obsolete/",
            response_model=PartRevisionDTO, include_in_schema=False)
def obsolete_part(workspace_id: str, part_key: str,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    pr = svc.mark_obsolete(db, workspace_id, number, version, current_user.login)
    return map_revision(pr, db)


@router.put("/workspaces/{workspace_id}/parts/{part_key}/newVersion",
            response_model=PartRevisionDTO)
@router.put("/workspaces/{workspace_id}/parts/{part_key}/newVersion/",
            response_model=PartRevisionDTO, include_in_schema=False)
def new_version_part(workspace_id: str, part_key: str,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    pr = svc.create_new_version(db, workspace_id, number, version, current_user.login)
    return map_revision(pr, db)


@router.put("/workspaces/{workspace_id}/parts/{part_key}/tags",
            response_model=PartRevisionDTO)
@router.put("/workspaces/{workspace_id}/parts/{part_key}/tags/",
            response_model=PartRevisionDTO, include_in_schema=False)
def set_tags(workspace_id: str, part_key: str,
             body: dict = Body(...),
             current_user: Account = Depends(get_current_user),
             db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    pr = svc.set_tags(db, workspace_id, number, version, body.get("tags", []),
                      current_user_login=current_user.login)
    return map_revision(pr, db)


def _extract_tag_labels(body: dict) -> list[str]:
    """解析标签请求体：支持 TagListDTO {tags: [{label: "a"}]} 和简单格式 {tags: ["a"]}。"""
    raw_tags = body.get("tags", [])
    if not raw_tags:
        return []
    labels = []
    for item in raw_tags:
        if isinstance(item, dict):
            label = item.get("label", "")
            if label:
                labels.append(label)
        elif isinstance(item, str):
            labels.append(item)
    return labels


@router.post("/workspaces/{workspace_id}/parts/{part_key}/tags",
             response_model=PartRevisionDTO)
@router.post("/workspaces/{workspace_id}/parts/{part_key}/tags/",
             response_model=PartRevisionDTO, include_in_schema=False)
def add_tag(workspace_id: str, part_key: str,
            body: dict = Body(...),
            current_user: Account = Depends(get_current_user),
            db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    labels = _extract_tag_labels(body)
    pr = None
    for label in labels:
        pr = svc.add_tag(db, workspace_id, number, version, label)
    if pr is None:
        pr = svc.get_revision(db, workspace_id, number, version)
    return map_revision(pr, db)


@router.delete("/workspaces/{workspace_id}/parts/{part_key}/tags/{tag_label}",
               response_model=PartRevisionDTO)
@router.delete("/workspaces/{workspace_id}/parts/{part_key}/tags/{tag_label}/",
               response_model=PartRevisionDTO, include_in_schema=False)
def remove_tag(workspace_id: str, part_key: str, tag_label: str,
               current_user: Account = Depends(get_current_user),
               db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    pr = svc.remove_tag(db, workspace_id, number, version, tag_label)
    return map_revision(pr, db)


@router.get("/workspaces/{workspace_id}/parts/{part_key}/tags",
            response_model=list[str])
@router.get("/workspaces/{workspace_id}/parts/{part_key}/tags/",
            response_model=list[str], include_in_schema=False)
def get_tags(workspace_id: str, part_key: str,
             current_user: Account = Depends(get_current_user),
             db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    pr = svc.get_revision(db, workspace_id, number, version)
    return [t.label for t in (pr.tags or [])]


@router.post("/workspaces/{workspace_id}/parts/{part_key}/share",
             response_model=SharedPartDTO)
@router.post("/workspaces/{workspace_id}/parts/{part_key}/share/",
             response_model=SharedPartDTO, include_in_schema=False)
def share_part(workspace_id: str, part_key: str,
               body: dict = Body({}),
               current_user: Account = Depends(get_current_user),
               db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    svc.get_revision(db, workspace_id, number, version)
    shared_uuid = str(uuid.uuid4())
    password = body.get("password")
    expire_date_str = body.get("expireDate")
    password_hash = hashlib.md5(password.encode()).hexdigest() if password else None
    expire_date = datetime.fromisoformat(expire_date_str) if expire_date_str else None
    entity = SharedEntity(
        uuid=shared_uuid,
        dtype="SharedPart",
        creation_date=datetime.utcnow(),
        expire_date=expire_date,
        password=password_hash,
        author_workspace_id=workspace_id,
        author_login=current_user.login,
        workspace_id=workspace_id,
        entity_workspace_id=workspace_id,
        partmaster_partnumber=number,
        partrevision_version=version,
    )
    db.add(entity)
    db.commit()
    return {"uuid": shared_uuid, "workspaceId": workspace_id}


@router.put("/workspaces/{workspace_id}/parts/{part_key}/publish",
            response_model=PartRevisionDTO)
@router.put("/workspaces/{workspace_id}/parts/{part_key}/publish/",
            response_model=PartRevisionDTO, include_in_schema=False)
def publish_part(workspace_id: str, part_key: str,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    pr = svc.get_revision(db, workspace_id, number, version)
    pr.public_shared = True
    db.commit()
    return map_revision(pr, db)


@router.put("/workspaces/{workspace_id}/parts/{part_key}/unpublish",
            response_model=PartRevisionDTO)
@router.put("/workspaces/{workspace_id}/parts/{part_key}/unpublish/",
            response_model=PartRevisionDTO, include_in_schema=False)
def unpublish_part(workspace_id: str, part_key: str,
                   current_user: Account = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    pr = svc.get_revision(db, workspace_id, number, version)
    pr.public_shared = False
    db.commit()
    return map_revision(pr, db)


@router.put("/workspaces/{workspace_id}/parts/{part_key}/acl",
            response_model=AclIdDTO)
@router.put("/workspaces/{workspace_id}/parts/{part_key}/acl/",
            response_model=AclIdDTO, include_in_schema=False)
def update_part_acl(workspace_id: str, part_key: str, body: dict,
                    db: Session = Depends(get_db),
                    current_user: Account = Depends(get_current_user)):
    from app.core.exceptions import AccessRightException
    number, version = _split_part_key(part_key)
    pr = svc.get_revision(db, workspace_id, number, version)
    # 仅 revision 作者或工作区管理员可修改 ACL
    is_admin = db.execute(text(
        "SELECT 1 FROM workspace WHERE id=:w AND admin_login=:l"
    ), {"w": workspace_id, "l": current_user.login}).scalar()
    if pr.author_login != current_user.login and not is_admin:
        raise AccessRightException("AccessRightException", current_user.login)
    acl_id = getattr(pr, "acl_id", None)
    user_entries = body.get("userEntries", {})
    group_entries = body.get("groupEntries", {})
    new_acl_id = apply_acl(db, acl_id, user_entries, group_entries)
    if pr.acl_id != new_acl_id:
        pr.acl_id = new_acl_id
        db.commit()
    return {"aclId": new_acl_id}


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


@router.get("/workspaces/{workspace_id}/parts/{part_key}/used-by-as-component",
            response_model=list[PartRevisionDTO])
@router.get("/workspaces/{workspace_id}/parts/{part_key}/used-by-as-component/",
            response_model=list[PartRevisionDTO], include_in_schema=False)
def used_by_component(workspace_id: str, part_key: str,
                      current_user: Account = Depends(get_current_user),
                      db: Session = Depends(get_db)):
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


@router.get("/workspaces/{workspace_id}/parts/{part_key}/used-by-as-substitute",
            response_model=list[PartRevisionDTO])
@router.get("/workspaces/{workspace_id}/parts/{part_key}/used-by-as-substitute/",
            response_model=list[PartRevisionDTO], include_in_schema=False)
def used_by_substitute(workspace_id: str, part_key: str,
                       current_user: Account = Depends(get_current_user),
                       db: Session = Depends(get_db)):
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


@router.get("/workspaces/{workspace_id}/parts/{part_key}/instances",
            response_model=list[dict])
@router.get("/workspaces/{workspace_id}/parts/{part_key}/instances/",
            response_model=list[dict], include_in_schema=False)
def get_instances(workspace_id: str, part_key: str,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """返回零件及其子装配的所有叶子实例（对齐 Java PartResource.getInstancesUnderPart）。

    前端 InstancesManager 调用此端点获取 3D 场景数据。
    每个叶子实例包含：矩阵、几何文件列表、包围盒、属性。
    """
    parts = part_key.rsplit("-", 1)
    if len(parts) != 2:
        raise HTTPException(400, "partKey 格式应为 {number}-{version}，如 GD50_Frame-A")
    part_number, version = parts

    pi = db.query(PartIteration).filter(
        PartIteration.workspace_id == workspace_id,
        PartIteration.partmaster_partnumber == part_number,
        PartIteration.partrevision_version == version,
    ).order_by(PartIteration.iteration.desc()).first()

    if not pi:
        raise PartIterationNotFoundException(
            "PartIterationNotFoundException", workspace_id, part_number, version)

    result: list[dict] = []
    collect_leaf_instances(db, pi, identity_matrix(), [-1], result)
    return result


@router.get("/workspaces/{workspace_id}/parts/{part_key}/baselines",
            response_model=list[dict])
@router.get("/workspaces/{workspace_id}/parts/{part_key}/baselines/",
            response_model=list[dict], include_in_schema=False)
def get_baselines(workspace_id: str, part_key: str,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)

    from app.models.configuration.baselined_part import BaselinedPart
    from app.models.configuration.product_baseline import ProductBaseline

    subq = (
        db.query(BaselinedPart.partcollection_id)
        .filter(
            BaselinedPart.target_workspace_id == workspace_id,
            BaselinedPart.target_partmaster_partnumber == number,
            BaselinedPart.target_partrevision_version == version,
        )
        .subquery()
    )

    baselines = (
        db.query(ProductBaseline)
        .filter(ProductBaseline.partcollection_id.in_(subq))
        .order_by(ProductBaseline.name)
        .all()
    )

    return [
        {
            "id": b.id,
            "name": b.name,
            "description": b.description,
            "type": b.type,
            "configurationItemId": b.configurationitem_id,
            "creationDate": b.creation_date.isoformat() if b.creation_date else None,
        }
        for b in baselines
    ]


@router.get("/workspaces/{workspace_id}/parts/{part_key}/aborted-workflows",
            response_model=list[WorkflowAbortedDTO])
@router.get("/workspaces/{workspace_id}/parts/{part_key}/aborted-workflows/",
            response_model=list[WorkflowAbortedDTO], include_in_schema=False)
def get_aborted_workflows(workspace_id: str, part_key: str,
                          current_user: Account = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    return workflow_service.get_aborted_workflows_for_part(
        db, workspace_id, number, version)


@router.get("/workspaces/{workspace_id}/parts/{part_key}/used-by-product-instance-masters",
            response_model=list[dict])
@router.get("/workspaces/{workspace_id}/parts/{part_key}/used-by-product-instance-masters/",
            response_model=list[dict], include_in_schema=False)
def used_by_product(workspace_id: str, part_key: str,
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)

    from app.models.configuration.baselined_part import BaselinedPart
    from app.models.configuration.product_baseline import ProductBaseline
    from app.models.configuration.product_instance_master import ProductInstanceMaster
    from sqlalchemy import and_

    results = (
        db.query(ProductInstanceMaster)
        .distinct()
        .join(
            ProductBaseline,
            and_(
                ProductBaseline.configurationitem_workspace_id == ProductInstanceMaster.workspace_id,
                ProductBaseline.configurationitem_id == ProductInstanceMaster.configurationitem_id,
            ),
        )
        .join(
            BaselinedPart,
            BaselinedPart.partcollection_id == ProductBaseline.partcollection_id,
        )
        .filter(
            BaselinedPart.target_workspace_id == workspace_id,
            BaselinedPart.target_partmaster_partnumber == number,
            BaselinedPart.target_partrevision_version == version,
        )
        .order_by(ProductBaseline.configurationitem_id)
        .all()
    )

    return [
        {
            "serialNumber": pim.serialnumber,
            "configurationItemId": pim.configurationitem_id,
            "workspaceId": pim.workspace_id,
            "productInstanceIterations": None,
            "acl": None,
        }
        for pim in results
    ]


@router.get("/workspaces/{workspace_id}/parts/{pn}/filter/{baseline_id}",
            response_model=list[dict])
@router.get("/workspaces/{workspace_id}/parts/{pn}/filter/{baseline_id}/",
            response_model=list[dict], include_in_schema=False)
def filter_by_baseline(workspace_id: str, pn: str, baseline_id: str,
                       current_user: Account = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    from app.models.configuration.baselined_part import BaselinedPart
    from app.models.configuration.product_baseline import ProductBaseline

    try:
        bl_id = int(baseline_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="baseline_id 必须是整数")

    baseline = db.query(ProductBaseline).filter(ProductBaseline.id == bl_id).first()
    if baseline is None:
        raise HTTPException(status_code=404, detail="Baseline not found")
    if baseline.configurationitem_workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Baseline not in this workspace")

    bp = (
        db.query(BaselinedPart)
        .filter(
            BaselinedPart.partcollection_id == baseline.partcollection_id,
            BaselinedPart.target_workspace_id == workspace_id,
            BaselinedPart.target_partmaster_partnumber == pn,
        )
        .first()
    )

    if bp is None:
        raise HTTPException(status_code=404, detail="Part not found in baseline")

    pi = (
        db.query(PartIteration)
        .filter(
            PartIteration.workspace_id == workspace_id,
            PartIteration.partmaster_partnumber == pn,
            PartIteration.partrevision_version == bp.target_partrevision_version,
            PartIteration.iteration == bp.target_iteration,
        )
        .first()
    )

    if pi is None:
        raise HTTPException(status_code=404, detail="Part iteration not found in database")

    return [map_revision(pi.revision, db)]


@router.put("/workspaces/{workspace_id}/parts/{part_key}/iterations/{iteration}/conversion",
            response_model=StatusDTO)
@router.put("/workspaces/{workspace_id}/parts/{part_key}/iterations/{iteration}/conversion/",
            response_model=StatusDTO, include_in_schema=False)
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
