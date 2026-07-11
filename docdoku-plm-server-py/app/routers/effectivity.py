"""效应端点（EffectivityResource + PartEffectivityResource）。

GET/POST  /workspaces/{ws}/parts/{part_key}/effectivities
DELETE    /workspaces/{ws}/parts/{part_key}/effectivities/{effectivity_id}
GET/PUT   /effectivities/{id}
"""
import re
from datetime import datetime
from fastapi import APIRouter, Depends, Body
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import CreationException
from app.models.auth import Account
from app.models.product.effectivity import Effectivity
from app.services.effectivity_manager import effectivity_service

router = APIRouter(prefix="/docdoku-plm-server-rest/api")


def _split_part_key(part_key: str) -> tuple[str, str]:
    m = re.match(r'^(.+)-([A-Z]+)$', part_key)
    if not m:
        from fastapi import HTTPException
        raise HTTPException(400, f"Invalid part key format: {part_key}")
    return m.group(1), m.group(2)


def _effectivity_to_dto(eff) -> dict:
    """将 Effectivity 行或 ORM 对象转换为 DTO。"""
    if hasattr(eff, '_mapping'):
        # 原生 SQL 行
        d = dict(eff._mapping)
    elif isinstance(eff, dict):
        d = eff
    else:
        # ORM 对象
        d = {k: v for k, v in vars(eff).items() if not k.startswith('_sa_')}

    dtype = d.get("dtype", "")
    dto: dict = {
        "id": d.get("id"),
        "name": d.get("name", ""),
        "description": d.get("description", ""),
        "configurationItemNumber": d.get("configurationitem_id"),
        "workspaceId": d.get("configurationitem_workspace_id"),
    }
    if dtype == "DateBasedEffectivity":
        dto["typeEffectivity"] = "DATEBASEDEFFECTIVITY"
        dto["startDate"] = d.get("start_date") or d.get("startdate")
        dto["endDate"] = d.get("end_date") or d.get("enddate")
    elif dtype == "SerialNumberBasedEffectivity":
        dto["typeEffectivity"] = "SERIALNUMBERBASEDEFFECTIVITY"
        dto["startNumber"] = d.get("start_number") or d.get("startnumber")
        dto["endNumber"] = d.get("end_number") or d.get("endnumber")
    elif dtype == "LotBasedEffectivity":
        dto["typeEffectivity"] = "LOTBASEDEFFECTIVITY"
        dto["startLotId"] = d.get("start_lot") or d.get("startlotid")
        dto["endLotId"] = d.get("end_lot") or d.get("endlotid")
    else:
        dto["typeEffectivity"] = "DATEBASEDEFFECTIVITY"
    return dto


@router.get("/workspaces/{workspace_id}/parts/{part_key}/effectivities")
@router.get("/workspaces/{workspace_id}/parts/{part_key}/effectivities/", include_in_schema=False)
def get_effectivities(
    workspace_id: str,
    part_key: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取零件版本的所有有效性条目。"""
    part_number, version = _split_part_key(part_key)
    rows = db.execute(text(
        "SELECT e.* FROM effectivity e "
        "JOIN partrevision_effectivity pre ON pre.effectivity_id = e.id "
        "WHERE pre.partmaster_workspace_id = :ws "
        "AND pre.partmaster_partnumber = :pn "
        "AND pre.partrevision_version = :ver"
    ), {"ws": workspace_id, "pn": part_number, "ver": version}).fetchall()
    return [_effectivity_to_dto(r) for r in rows]


@router.post("/workspaces/{workspace_id}/parts/{part_key}/effectivities", status_code=201)
@router.post("/workspaces/{workspace_id}/parts/{part_key}/effectivities/", status_code=201, include_in_schema=False)
def create_effectivity(
    workspace_id: str,
    part_key: str,
    body: dict = Body(...),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建零件版本有效性（日期/序列号/批次号）。"""
    part_number, version = _split_part_key(part_key)
    type_eff = body.get("typeEffectivity", "DATEBASEDEFFECTIVITY")
    ci_id = body.get("configurationItemNumber")
    name = body.get("name", "")
    description = body.get("description", "")

    if type_eff == "DATEBASEDEFFECTIVITY":
        if not body.get("startDate"):
            raise CreationException("startDate is required for DateBasedEffectivity")
        dtype = "DateBasedEffectivity"
        eff = Effectivity(
            dtype=dtype, name=name, description=description,
            start_date=_parse_date(body.get("startDate")),
            end_date=_parse_date(body.get("endDate")),
            configurationitem_id=ci_id,
            configurationitem_workspace_id=workspace_id,
        )
    elif type_eff == "SERIALNUMBERBASEDEFFECTIVITY":
        if not body.get("startNumber"):
            raise CreationException("startNumber is required for SerialNumberBasedEffectivity")
        dtype = "SerialNumberBasedEffectivity"
        eff = Effectivity(
            dtype=dtype, name=name, description=description,
            start_number=body.get("startNumber"),
            end_number=body.get("endNumber"),
            configurationitem_id=ci_id,
            configurationitem_workspace_id=workspace_id,
        )
    else:  # LOTBASEDEFFECTIVITY
        if not body.get("startLotId"):
            raise CreationException("startLotId is required for LotBasedEffectivity")
        dtype = "LotBasedEffectivity"
        eff = Effectivity(
            dtype=dtype, name=name, description=description,
            start_lot=body.get("startLotId"),
            end_lot=body.get("endLotId"),
            configurationitem_id=ci_id,
            configurationitem_workspace_id=workspace_id,
        )

    db.add(eff)
    db.flush()

    # 关联到 partrevision
    db.execute(text(
        "INSERT INTO partrevision_effectivity "
        "(partmaster_workspace_id, partmaster_partnumber, partrevision_version, effectivity_id) "
        "VALUES (:ws, :pn, :ver, :eid)"
    ), {"ws": workspace_id, "pn": part_number, "ver": version, "eid": eff.id})
    db.commit()
    db.refresh(eff)
    return _effectivity_to_dto(eff)


@router.delete("/workspaces/{workspace_id}/parts/{part_key}/effectivities/{effectivity_id}", status_code=204)
@router.delete("/workspaces/{workspace_id}/parts/{part_key}/effectivities/{effectivity_id}/",
               status_code=204, include_in_schema=False)
def delete_effectivity(
    workspace_id: str,
    part_key: str,
    effectivity_id: int,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除零件版本有效性。"""
    effectivity_service.delete_effectivity(db, workspace_id,
                                           *_split_part_key(part_key), effectivity_id)
    return Response(status_code=204)


@router.get("/workspaces/{workspace_id}/effectivities/{id}")
@router.get("/workspaces/{workspace_id}/effectivities/{id}/", include_in_schema=False)
def get_effectivity(
    workspace_id: str,
    id: int,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """按 ID 获取有效性条目。"""
    eff = db.query(Effectivity).filter(Effectivity.id == id).first()
    if eff is None:
        from app.core.exceptions import EntityNotFoundException
        raise EntityNotFoundException("EffectivityNotFoundException", str(id))
    return _effectivity_to_dto(eff)


@router.put("/workspaces/{workspace_id}/effectivities/{id}", status_code=204)
@router.put("/workspaces/{workspace_id}/effectivities/{id}/", status_code=204, include_in_schema=False)
def put_effectivity(
    workspace_id: str,
    id: int,
    body: dict = Body(...),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新有效性条目。"""
    eff = db.query(Effectivity).filter(Effectivity.id == id).first()
    if eff is None:
        from app.core.exceptions import EntityNotFoundException
        raise EntityNotFoundException("EffectivityNotFoundException", str(id))
    if "name" in body:
        eff.name = body["name"]
    if "description" in body:
        eff.description = body["description"]
    if "startDate" in body:
        eff.start_date = _parse_date(body["startDate"])
    if "endDate" in body:
        eff.end_date = _parse_date(body["endDate"])
    if "startNumber" in body:
        eff.start_number = body["startNumber"]
    if "endNumber" in body:
        eff.end_number = body["endNumber"]
    if "startLotId" in body:
        eff.start_lot = body["startLotId"]
    if "endLotId" in body:
        eff.end_lot = body["endLotId"]
    db.commit()
    return Response(status_code=204)


def _parse_date(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
