"""单个零件 CRUD（PartResource）。"""
import re
from fastapi import APIRouter, Depends, HTTPException, Body, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import (
    PartIterationNotFoundException,
)
from app.models.auth import Account
from app.schemas.part import PartRevisionDTO, PartIterationDTO, PartIterationUpdateDTO, ConversionDTO, ConversionResultDTO, StatusDTO, SharedPartDTO, AclIdDTO
from app.schemas.workflow import WorkflowAbortedDTO
from app.services.product_manager import ProductService
from app.services.part_mapper import map_revision, map_iteration
from app.services import converter
from app.services.workflow_manager import workflow_service

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
            status_code=204)
@router.put("/workspaces/{workspace_id}/parts/{part_key}/newVersion/",
            status_code=204, include_in_schema=False)
def new_version_part(workspace_id: str, part_key: str,
                     body: dict = Body({}),
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    svc.create_new_version(db, workspace_id, number, version, current_user.login)
    if body.get("description"):
        svc.set_new_version_description(db, workspace_id, number, version,
                                         body["description"])
    # TODO: newVersion 尚缺 workflowModelId/acl/roleMapping 传递（service.create_new_version 暂不支持）。
    #       对应 Java PartResource.createNewPartVersion(PartCreationDTO: description/workflowModelId/acl/roleMapping)。
    #       需扩展 product_manager.create_new_version 支持 workflowModelId/acl_id/roleMapping 参数。


@router.put("/workspaces/{workspace_id}/parts/{part_key}/tags",
            response_model=PartRevisionDTO)
@router.put("/workspaces/{workspace_id}/parts/{part_key}/tags/",
            response_model=PartRevisionDTO, include_in_schema=False)
def set_tags(workspace_id: str, part_key: str,
             body: dict = Body(...),
             current_user: Account = Depends(get_current_user),
             db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    labels = _extract_tag_labels(body)
    pr = svc.set_tags(db, workspace_id, number, version, labels,
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
        pr = svc.add_tag(db, workspace_id, number, version, label,
                         current_user_login=current_user.login)
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
    shared_uuid = svc.share_part(db, workspace_id, number, version,
                                  current_user.login,
                                  password=body.get("password"),
                                  expire_date_str=body.get("expireDate"))
    return {"uuid": shared_uuid, "workspaceId": workspace_id}


@router.delete("/workspaces/{workspace_id}/parts/{part_key}/iterations/{iteration}/files/{sub_type}/{file_name}",
               status_code=204)
@router.delete("/workspaces/{workspace_id}/parts/{part_key}/iterations/{iteration}/files/{sub_type}/{file_name}/",
               status_code=204, include_in_schema=False)
def delete_part_file_subresource(
    workspace_id: str, part_key: str, iteration: int,
    sub_type: str, file_name: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """SubResource 路径删除文件（对齐 Java PartResource.removeFile）。"""
    number, version = _split_part_key(part_key)
    svc.delete_part_file_subresource(db, workspace_id, number, version,
                                      iteration, sub_type, file_name,
                                      current_user.login)


@router.put("/workspaces/{workspace_id}/parts/{part_key}/publish",
            status_code=204)
@router.put("/workspaces/{workspace_id}/parts/{part_key}/publish/",
            status_code=204, include_in_schema=False)
def publish_part(workspace_id: str, part_key: str,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    svc.publish_revision(db, workspace_id, number, version, current_user.login)


@router.put("/workspaces/{workspace_id}/parts/{part_key}/unpublish",
            status_code=204)
@router.put("/workspaces/{workspace_id}/parts/{part_key}/unpublish/",
            status_code=204, include_in_schema=False)
def unpublish_part(workspace_id: str, part_key: str,
                   current_user: Account = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    svc.unpublish_revision(db, workspace_id, number, version, current_user.login)


@router.put("/workspaces/{workspace_id}/parts/{part_key}/acl",
            status_code=204)
@router.put("/workspaces/{workspace_id}/parts/{part_key}/acl/",
            status_code=204, include_in_schema=False)
def update_part_acl(workspace_id: str, part_key: str, body: dict,
                    db: Session = Depends(get_db),
                    current_user: Account = Depends(get_current_user)):
    number, version = _split_part_key(part_key)
    svc.update_part_acl(db, workspace_id, number, version,
                         current_user.login, body)


@router.get("/workspaces/{workspace_id}/parts/{part_number}/latest-revision",
             response_model=PartRevisionDTO)
def get_latest_revision(
    workspace_id: str,
    part_number: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    is_admin = db.execute(text(
        "SELECT 1 FROM usergroupmapping WHERE login=:l AND groupname='admin'"
    ), {"l": current_user.login}).first() is not None
    pr = svc.get_latest_revision(db, workspace_id, part_number,
                                 current_user_login=current_user.login,
                                 is_admin=is_admin)
    return map_revision(pr, db)


@router.get("/workspaces/{workspace_id}/parts/{part_key}/used-by-as-component",
            response_model=list[PartRevisionDTO])
@router.get("/workspaces/{workspace_id}/parts/{part_key}/used-by-as-component/",
            response_model=list[PartRevisionDTO], include_in_schema=False)
def used_by_component(workspace_id: str, part_key: str,
                      current_user: Account = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    rows = svc.get_used_by_as_component(db, workspace_id, number, version)
    result = []
    for ws, pn, v in rows:
        pr = svc.get_revision(db, ws, pn, v)
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
    rows = svc.get_used_by_as_substitute(db, workspace_id, number, version)
    result = []
    for ws, pn, v in rows:
        pr = svc.get_revision(db, ws, pn, v)
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
    return svc.get_leaf_instances(db, workspace_id, part_key)


@router.get("/workspaces/{workspace_id}/parts/{part_key}/baselines",
            response_model=list[dict])
@router.get("/workspaces/{workspace_id}/parts/{part_key}/baselines/",
            response_model=list[dict], include_in_schema=False)
def get_baselines(workspace_id: str, part_key: str,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    return svc.get_baselines_for_part(db, workspace_id, number, version)


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
    return svc.get_used_by_product_instances(db, workspace_id, number, version)


@router.get("/workspaces/{workspace_id}/parts/{pn}/filter/{baseline_id}",
            response_model=PartIterationDTO)
@router.get("/workspaces/{workspace_id}/parts/{pn}/filter/{baseline_id}/",
            response_model=PartIterationDTO, include_in_schema=False)
def filter_by_baseline(workspace_id: str, pn: str, baseline_id: str,
                       current_user: Account = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """对齐 Java PartsResource.filterPartMasterInBaseline: 返回单个 PartIterationDTO"""
    pi = svc.filter_by_baseline(db, workspace_id, pn, baseline_id)
    return map_iteration(pi, db)


@router.put("/workspaces/{workspace_id}/parts/{part_key}/iterations/{iteration}/conversion",
            status_code=204)
@router.put("/workspaces/{workspace_id}/parts/{part_key}/iterations/{iteration}/conversion/",
            status_code=204, include_in_schema=False)
def retry_conversion(workspace_id: str, part_key: str, iteration: int,
                     request: Request,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    from app.services.kafka_producer import send_conversion_order
    number, version = _split_part_key(part_key)
    filename, _pi = svc.retry_conversion(db, workspace_id, number, version, iteration)
    auth = request.headers.get("authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    send_conversion_order(workspace_id, number, version, iteration, filename, token)
