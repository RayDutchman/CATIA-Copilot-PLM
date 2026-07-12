"""LOV（List of Values）管理——对标 Payara LOVManagerBean。

管理枚举值列表的 CRUD。
"""
from sqlalchemy.orm import Session
from sqlalchemy import text


class LOVService:
    """LOV 管理服务。"""

    def find_lov_from_workspace(self, db: Session, ws: str) -> list:
        rows = db.execute(text(
            "SELECT * FROM lov WHERE workspace_id = :ws"
        ), {"ws": ws}).fetchall()
        return [dict(r._mapping) for r in rows]

    def find_lov(self, db: Session, ws: str, lov_name: str) -> dict | None:
        row = db.execute(text(
            "SELECT * FROM lov WHERE workspace_id = :ws AND name = :n"
        ), {"ws": ws, "n": lov_name}).first()
        if not row:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("ListOfValuesNotFoundException", lov_name)
        return dict(row._mapping)

    def create_lov(self, db: Session, ws: str, name: str,
                    name_value_pairs: list) -> dict:
        db.execute(text(
            "INSERT INTO lov (workspace_id, name) VALUES (:ws, :n) "
            "ON CONFLICT (workspace_id, name) DO NOTHING"
        ), {"ws": ws, "n": name})
        for nvp in name_value_pairs:
            db.execute(text(
                "INSERT INTO lov_namevalue (lov_workspace_id, lov_name, name, value, namevalue_order) "
                "VALUES (:ws, :n, :an, :av, :ord)"
            ), {"ws": ws, "n": name,
                "an": nvp.get("name", ""), "av": nvp.get("value", ""),
                "ord": nvp.get("order", 0)})
        db.commit()
        return self.find_lov(db, ws, name)

    def delete_lov(self, db: Session, ws: str, lov_name: str) -> None:
        db.execute(text(
            "DELETE FROM lov WHERE workspace_id = :ws AND name = :n"
        ), {"ws": ws, "n": lov_name})
        db.commit()

    def update_lov(self, db: Session, ws: str, lov_name: str,
                    new_name: str, name_value_pairs: list) -> dict:
        db.execute(text(
            "UPDATE lov SET name = :nn WHERE workspace_id = :ws AND name = :n"
        ), {"ws": ws, "nn": new_name, "n": lov_name})
        db.execute(text(
            "DELETE FROM lov_namevalue WHERE lov_workspace_id = :ws AND lov_name = :n"
        ), {"ws": ws, "n": new_name})
        for nvp in name_value_pairs:
            db.execute(text(
                "INSERT INTO lov_namevalue (lov_workspace_id, lov_name, name, value, namevalue_order) "
                "VALUES (:ws, :n, :an, :av, :ord)"
            ), {"ws": ws, "n": new_name,
                "an": nvp.get("name", ""), "av": nvp.get("value", ""),
                "ord": nvp.get("order", 0)})
        db.commit()
        return self.find_lov(db, ws, new_name)

    def is_lov_deletable(self, db: Session, ws: str, lov_name: str) -> bool:
        """对齐 Java isLOVDeletable：检查 LOV 是否被任何模板或实际零件迭代引用。"""
        row = db.execute(text(
            "SELECT 1 FROM instanceattributetemplate "
            "WHERE lov_name = :n AND lov_workspace_id = :ws LIMIT 1"
        ), {"n": lov_name, "ws": ws}).first()
        if row:
            return False
        row = db.execute(text(
            "SELECT 1 FROM partiteration_pathdata_attr pa "
            "JOIN instanceattributetemplate iat ON iat.id = pa.instanceattribute_template_id "
            "WHERE iat.lov_name = :n AND iat.lov_workspace_id = :ws LIMIT 1"
        ), {"n": lov_name, "ws": ws}).first()
        return row is None


lov_service = LOVService()
