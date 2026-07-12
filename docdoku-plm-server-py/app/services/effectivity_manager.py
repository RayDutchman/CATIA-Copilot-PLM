"""分时有效性管理——对标 Payara EffectivityManagerBean。

管理零件版本的有效性（SerialNumber/Date/Lot based effectivity）。
"""
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.product.effectivity import Effectivity


class EffectivityService:
    """有效性管理服务。"""

    def get_effectivity(self, db: Session, ws: str, effectivity_id: int) -> dict:
        row = db.execute(text(
            "SELECT * FROM effectivity WHERE id = :id AND EXISTS(SELECT 1 FROM partrevision_effectivity pre WHERE pre.effectivity_id = :id AND pre.partmaster_workspace_id = :ws)"
        ), {"id": effectivity_id, "ws": ws}).first()
        if not row:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("EffectivityNotFoundException", str(effectivity_id))
        return dict(row._mapping)

    def create_effectivity(self, db: Session, ws: str, part_number: str,
                            version: str, body: dict) -> Effectivity:
        """创建有效性记录（D/S/L 自动按 typeEffectivity 分派）。"""
        type_eff = body.get("typeEffectivity", "DATEBASEDEFFECTIVITY")
        ci_id = body.get("configurationItemNumber")
        name = body.get("name", "")
        description = body.get("description", "")
        if type_eff == "SERIALNUMBERBASEDEFFECTIVITY":
            eff = Effectivity(
                dtype="SerialNumberBasedEffectivity", name=name, description=description,
                start_number=body.get("startNumber"),
                end_number=body.get("endNumber"),
                configurationitem_id=ci_id,
                configurationitem_workspace_id=ws,
            )
        elif type_eff == "LOTBASEDEFFECTIVITY":
            eff = Effectivity(
                dtype="LotBasedEffectivity", name=name, description=description,
                start_lot=body.get("startLotId"),
                end_lot=body.get("endLotId"),
                configurationitem_id=ci_id,
                configurationitem_workspace_id=ws,
            )
        else:
            eff = Effectivity(
                dtype="DateBasedEffectivity", name=name, description=description,
                start_date=_parse_date(body.get("startDate")),
                end_date=_parse_date(body.get("endDate")),
                configurationitem_id=ci_id,
                configurationitem_workspace_id=ws,
            )
        db.add(eff)
        db.flush()
        db.execute(text(
            "INSERT INTO partrevision_effectivity "
            "(partmaster_workspace_id, partmaster_partnumber, partrevision_version, effectivity_id) "
            "VALUES (:ws, :pn, :ver, :eid)"
        ), {"ws": ws, "pn": part_number, "ver": version, "eid": eff.id})
        db.commit()
        db.refresh(eff)
        return eff

    def update_effectivity(self, db: Session, ws: str, effectivity_id: int,
                            body: dict) -> Effectivity:
        """更新有效性记录的通用字段。"""
        eff = db.query(Effectivity).filter(Effectivity.id == effectivity_id).first()
        if not eff:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("EffectivityNotFoundException", str(effectivity_id))
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
        db.refresh(eff)
        return eff

    def delete_effectivity(self, db: Session, ws: str, part_number: str,
                            version: str, effectivity_id: int) -> None:
        """删除有效性：先确认 effectivity 归属当前 workspace，再删 join 表 + 主表。"""
        own = db.execute(text(
            "SELECT 1 FROM partrevision_effectivity "
            "WHERE effectivity_id = :id AND partmaster_workspace_id = :ws"
        ), {"id": effectivity_id, "ws": ws}).first()
        if not own:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("EffectivityNotFoundException", str(effectivity_id))
        db.execute(text(
            "DELETE FROM partrevision_effectivity WHERE effectivity_id = :id AND partmaster_workspace_id = :ws"
        ), {"id": effectivity_id, "ws": ws})
        db.execute(text(
            "DELETE FROM effectivity WHERE id = :id"
        ), {"id": effectivity_id})
        db.commit()


def _parse_date(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


effectivity_service = EffectivityService()
