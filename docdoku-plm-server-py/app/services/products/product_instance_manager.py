"""ProductInstanceManager——产品实例管理。

对齐 Java ProductInstanceManagerBean。
底层 delegate 到 ProductStructureService 的实例和 PathData 方法。
"""
from datetime import datetime
from sqlalchemy.orm import Session


class ProductInstanceService:
    """产品实例管理服务。"""

    def __init__(self):
        from app.services.product_structure import ProductStructureService
        self._product = ProductStructureService()

    def list_instances(self, db: Session, ws: str, ci_id: str = None) -> list:
        return [self._to_dict(m) for m in self._product.list_instances(db, ws, ci_id)]

    def get_instance(self, db: Session, ws: str, ci_id: str, serial: str) -> dict:
        from sqlalchemy import text
        m = db.execute(text(
            "SELECT * FROM productinstancemaster "
            "WHERE workspace_id=:ws AND configurationitem_id=:ci AND serialnumber=:sn"
        ), {"ws": ws, "ci": ci_id, "sn": serial}).first()
        if not m:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("ProductInstanceMasterNotFoundException", serial)
        return self._to_row(m)

    def create_instance(self, db: Session, ws: str, ci_id: str, serial: str,
                         baseline_id: int, user_login: str,
                         effectivity_date: datetime = None,
                         effectivity_serial: str = None,
                         effectivity_lot: str = None) -> dict:
        """创建产品实例。可基于已有基线或 effectivity 过滤创建。"""
        return self._to_dict(
            self._product.create_instance(db, ws, ci_id, serial, baseline_id, user_login))

    def update_instance(self, db: Session, ws: str, ci_id: str, serial: str,
                         iteration_note: str = "") -> dict:
        """更新产品实例迭代。"""
        from sqlalchemy import text
        inst = self.get_instance(db, ws, ci_id, serial)
        db.execute(text(
            "UPDATE productinstanceiteration SET iterationnote=:note "
            "WHERE workspace_id=:ws AND configurationitem_id=:ci "
            "AND prdinstancemaster_serialnumber=:sn AND iteration=:it"
        ), {"ws": ws, "ci": ci_id, "sn": serial, "it": 1, "note": iteration_note})
        db.commit()
        return inst

    def delete_instance(self, db: Session, ws: str, ci_id: str, serial: str):
        return self._product.delete_instance(db, ws, ci_id, serial)

    def get_instance_iterations(self, db: Session, ws: str, ci_id: str,
                                 serial: str) -> list:
        """获取产品实例的所有迭代。"""
        from sqlalchemy import text
        rows = db.execute(text(
            "SELECT * FROM productinstanceiteration "
            "WHERE workspace_id=:ws AND configurationitem_id=:ci "
            "AND prdinstancemaster_serialnumber=:sn ORDER BY iteration"
        ), {"ws": ws, "ci": ci_id, "sn": serial}).fetchall()
        return [{"iteration": r[0], "note": r[1] if len(r) > 1 else "",
                 "author": r[2] if len(r) > 2 else "",
                 "creationDate": str(r[3]) if len(r) > 3 else "",
                 "baselineId": r[4] if len(r) > 4 else None}
                for r in rows]

    def get_path_data_masters(self, db: Session, ws: str, ci_id: str,
                               serial: str) -> list:
        """获取产品实例的所有 PathDataMaster。"""
        from sqlalchemy import text
        rows = db.execute(text(
            "SELECT * FROM pathdatamaster "
            "WHERE workspace_id=:ws AND configurationitem_id=:ci "
            "AND prdinstancemaster_serialnumber=:sn"
        ), {"ws": ws, "ci": ci_id, "sn": serial}).fetchall()
        return [{"id": r[0], "path": r[1] if len(r) > 1 else "",
                 "name": r[2] if len(r) > 2 else "",
                 "description": r[3] if len(r) > 3 else ""}
                for r in rows]

    def _to_dict(self, m) -> dict:
        return {"serialNumber": m.serialnumber, "workspaceId": m.workspace_id,
                "configurationItemId": m.configurationitem_id}

    def _to_row(self, row) -> dict:
        return {"serialNumber": row[2] if len(row) > 2 else "",
                "workspaceId": row[0] if len(row) > 0 else "",
                "configurationItemId": row[1] if len(row) > 1 else ""}


product_instance_service = ProductInstanceService()
