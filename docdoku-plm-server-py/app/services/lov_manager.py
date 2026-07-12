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

    def get_lovs_with_values(self, db: Session, ws: str) -> dict:
        """获取workspace所有LOV及其值，返回 {name: [{name, value}]}"""
        rows = db.execute(text(
            "SELECT l.name FROM lov l WHERE l.workspace_id = :ws ORDER BY l.name"
        ), {"ws": ws}).fetchall()
        result = {}
        for r in rows:
            name = r[0]
            nv_rows = db.execute(text(
                "SELECT nv.name, nv.value FROM lov_namevalue nv "
                "WHERE nv.lov_name = :name AND nv.lov_workspace_id = :ws "
                "ORDER BY nv.namevalue_order"
            ), {"name": name, "ws": ws}).fetchall()
            result[name] = [{"name": n[0], "value": n[1]} for n in nv_rows]
        return result

    def lov_exists(self, db: Session, ws: str, lov_name: str) -> bool:
        """检查指定workspace中是否存在指定名称的LOV。"""
        return db.execute(text(
            "SELECT 1 FROM lov WHERE name = :name AND workspace_id = :ws"
        ), {"name": lov_name, "ws": ws}).first() is not None

    def create_lov(self, db: Session, ws: str, name: str,
                    name_value_pairs: list, check_exists: bool = True) -> dict:
        if check_exists:
            existing = db.execute(text(
                "SELECT name FROM lov WHERE name = :name AND workspace_id = :ws"
            ), {"name": name, "ws": ws}).fetchone()
            if existing:
                from app.core.exceptions import EntityAlreadyExistsException
                raise EntityAlreadyExistsException("LOVAlreadyExistsException", name)
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
            "DELETE FROM lov_namevalue WHERE lov_name = :n AND lov_workspace_id = :ws"
        ), {"n": lov_name, "ws": ws})
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

    def build_lov_dto(self, db: Session, ws: str, lov_row: dict) -> dict:
        """将 lov 行 + 关联 namevalues 组装成 DTO。"""
        attrs = db.execute(text(
            "SELECT name, value FROM lov_namevalue "
            "WHERE lov_workspace_id = :ws AND lov_name = :n ORDER BY namevalue_order"
        ), {"ws": ws, "n": lov_row["name"]}).fetchall()
        return {
            "name": lov_row["name"],
            "workspaceId": lov_row["workspace_id"],
            "values": [{"name": r[0], "value": r[1]} for r in attrs],
        }

    def is_lov_deletable(self, db: Session, ws: str, lov_name: str) -> bool:
        """对齐 Java isLOVDeletable：检查 LOV 是否被任何模板或实际零件迭代引用。

        三条件（对齐 Java LOVManagerBean）：
        ① instanceattributetemplate 直接引用 (lov_name/lov_workspace_id)
        ② partiteration_pathdata_attr → instanceattributetemplate（迭代路径数据属性模板）
        ③ partiteration_attribute → instanceattribute → 通过 name 关联 instanceattributetemplate
           （实际零件迭代的 InstanceListOfValuesAttribute 实例属性使用）
        """
        # 条件①：检查是否有模板直接引用此 LOV
        row = db.execute(text(
            "SELECT 1 FROM instanceattributetemplate "
            "WHERE lov_name = :n AND lov_workspace_id = :ws LIMIT 1"
        ), {"n": lov_name, "ws": ws}).first()
        if row:
            return False
        # 条件②：检查 PartIteration 的路径数据属性模板是否引用此 LOV
        row = db.execute(text(
            "SELECT 1 FROM partiteration_pathdata_attr pa "
            "JOIN instanceattributetemplate iat ON iat.id = pa.instanceattribute_template_id "
            "WHERE iat.lov_name = :n AND iat.lov_workspace_id = :ws LIMIT 1"
        ), {"n": lov_name, "ws": ws}).first()
        if row:
            return False
        # 条件③：检查实际零件迭代的实例属性（instanceattribute）是否来自引用此 LOV 的模板
        # instanceattribute 表无 lov_name/lov_workspace_id 列，通过 name 与模板关联
        row = db.execute(text(
            "SELECT 1 FROM partiteration_attribute pa "
            "JOIN instanceattribute ia ON ia.id = pa.instanceattribute_id "
            "JOIN instanceattributetemplate iat ON iat.name = ia.name "
            "WHERE iat.lov_name = :n AND iat.lov_workspace_id = :ws LIMIT 1"
        ), {"n": lov_name, "ws": ws}).first()
        return row is None


lov_service = LOVService()
