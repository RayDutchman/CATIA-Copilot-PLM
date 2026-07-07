"""LOV（List of Values）管理——对标 Payara LOVManagerBean。

管理枚举值列表的 CRUD。
"""
from sqlalchemy.orm import Session
from sqlalchemy import text


class LOVService:
    """LOV 管理服务。"""

    def find_lov_from_workspace(self, db: Session, ws: str) -> list:
        rows = db.execute(text(
            "SELECT * FROM listofvalues WHERE workspace_id = :ws"
        ), {"ws": ws}).fetchall()
        return [dict(r._mapping) for r in rows]

    def find_lov(self, db: Session, ws: str, lov_name: str) -> dict | None:
        row = db.execute(text(
            "SELECT * FROM listofvalues WHERE workspace_id = :ws AND name = :n"
        ), {"ws": ws, "n": lov_name}).first()
        if not row:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("ListOfValuesNotFoundException", lov_name)
        return dict(row._mapping)

    def create_lov(self, db: Session, ws: str, name: str,
                    name_value_pairs: list) -> dict:
        db.execute(text(
            "INSERT INTO listofvalues (workspace_id, name) VALUES (:ws, :n) "
            "ON CONFLICT (workspace_id, name) DO NOTHING"
        ), {"ws": ws, "n": name})
        for nvp in name_value_pairs:
            db.execute(text(
                "INSERT INTO listofvaluesattribute (workspace_id, lov_name, attr_name, attr_value) "
                "VALUES (:ws, :n, :an, :av)"
            ), {"ws": ws, "n": name,
                "an": nvp.get("name", ""), "av": nvp.get("value", "")})
        db.commit()
        return self.find_lov(db, ws, name)

    def delete_lov(self, db: Session, ws: str, lov_name: str) -> None:
        db.execute(text(
            "DELETE FROM listofvalues WHERE workspace_id = :ws AND name = :n"
        ), {"ws": ws, "n": lov_name})
        db.commit()

    def update_lov(self, db: Session, ws: str, lov_name: str,
                    new_name: str, name_value_pairs: list) -> dict:
        db.execute(text(
            "UPDATE listofvalues SET name = :nn WHERE workspace_id = :ws AND name = :n"
        ), {"ws": ws, "nn": new_name, "n": lov_name})
        db.execute(text(
            "DELETE FROM listofvaluesattribute WHERE workspace_id = :ws AND lov_name = :n"
        ), {"ws": ws, "n": new_name})
        for nvp in name_value_pairs:
            db.execute(text(
                "INSERT INTO listofvaluesattribute (workspace_id, lov_name, attr_name, attr_value) "
                "VALUES (:ws, :n, :an, :av)"
            ), {"ws": ws, "n": new_name,
                "an": nvp.get("name", ""), "av": nvp.get("value", "")})
        db.commit()
        return self.find_lov(db, ws, new_name)

    def is_lov_deletable(self, db: Session, ws: str, lov_name: str) -> bool:
        # TODO: 检查是否有模板引用此 LOV
        return True


lov_service = LOVService()
