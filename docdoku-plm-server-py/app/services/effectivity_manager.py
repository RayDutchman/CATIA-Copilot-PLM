"""分时有效性管理——对标 Payara EffectivityManagerBean。

管理零件版本的有效性（SerialNumber/Date/Lot based effectivity）。
TODO: 完整实现 CRUD 逻辑。
"""
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text


class EffectivityService:
    """有效性管理服务。"""

    def get_effectivity(self, db: Session, ws: str, effectivity_id: int) -> dict:
        row = db.execute(text(
            "SELECT * FROM effectivity WHERE id = :id AND workspace_id = :ws"
        ), {"id": effectivity_id, "ws": ws}).first()
        if not row:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("EffectivityNotFoundException", str(effectivity_id))
        return dict(row._mapping)

    def delete_effectivity(self, db: Session, ws: str, part_number: str,
                            version: str, effectivity_id: int) -> None:
        db.execute(text(
            "DELETE FROM effectivity WHERE id = :id AND workspace_id = :ws"
        ), {"id": effectivity_id, "ws": ws})
        db.commit()

    # TODO: create/update methods for SerialNumberBased, DateBased, LotBased effectivities


effectivity_service = EffectivityService()
