"""DocumentBaselineManager——文档基线管理。

对齐 Java DocumentBaselineManagerBean。
"""
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text


class DocumentBaselineService:
    """文档基线管理服务。"""

    def create_baseline(self, db: Session, ws: str, name: str,
                         baseline_type: int, description: str = "",
                         document_revision_keys: list = None,
                         user_login: str = "") -> dict:
        """创建文档基线。纳入指定的文档修订版。"""
        if not document_revision_keys:
            raise ValueError("document_revision_keys required")

        db.execute(text(
            "INSERT INTO documentbaseline "
            "(name, description, creationdate, author_workspace_id, author_login, "
            "type, workspace_id) "
            "VALUES (:name, :desc, now(), :ws, :login, :typ, :ws)"
        ), {"name": name, "desc": description, "ws": ws,
            "login": user_login, "typ": baseline_type})
        db.flush()

        bl_id = db.execute(text(
            "SELECT currval('documentbaseline_id_seq')")).scalar()

        # 创建 DocumentCollection
        db.execute(text(
            "INSERT INTO documentcollection (creationdate, author_workspace_id, author_login) "
            "VALUES (now(), :ws, :login)"
        ), {"ws": ws, "login": user_login})
        db.flush()
        dc_id = db.execute(text("SELECT currval('documentcollection_id_seq')")).scalar()

        # 关联文档
        for key in document_revision_keys:
            db.execute(text(
                "INSERT INTO baselineddocument "
                "(target_workspace_id, target_documentmaster_id, "
                "target_documentrevision_version, target_iteration, "
                "documentcollection_id) "
                "VALUES (:ws, :did, :ver, :iter, :dcid)"
            ), {"ws": ws, "did": key.get("documentMasterId", ""),
                "ver": key.get("version", "A"), "iter": key.get("iteration", 1),
                "dcid": dc_id})

        db.execute(text(
            "UPDATE documentbaseline SET documentcollection_id=:dcid WHERE id=:bid"
        ), {"dcid": dc_id, "bid": bl_id})

        db.commit()
        return {"id": bl_id, "name": name, "description": description, "type": baseline_type}

    def get_baselines(self, db: Session, ws: str) -> list:
        rows = db.execute(text(
            "SELECT * FROM documentbaseline WHERE workspace_id=:ws ORDER BY id"
        ), {"ws": ws}).fetchall()
        return [{"id": r[0], "name": r[1], "description": r[2] if len(r) > 2 else "",
                 "type": r[3] if len(r) > 3 else 0,
                 "creationDate": str(r[4]) if len(r) > 4 else ""}
                for r in rows]

    def get_baseline(self, db: Session, ws: str, baseline_id: int) -> dict:
        row = db.execute(text(
            "SELECT * FROM documentbaseline WHERE id=:id AND workspace_id=:ws"
        ), {"id": baseline_id, "ws": ws}).first()
        if not row:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("BaselineNotFoundException", str(baseline_id))
        return {"id": row[0], "name": row[1], "description": row[2] if len(row) > 2 else "",
                "type": row[3] if len(row) > 3 else 0}

    def delete_baseline(self, db: Session, ws: str, baseline_id: int):
        bl = self.get_baseline(db, ws, baseline_id)
        dc_id = bl.get("documentCollectionId")
        if dc_id:
            db.execute(text(
                "DELETE FROM baselineddocument WHERE documentcollection_id=:dcid"
            ), {"dcid": dc_id})
            db.execute(text(
                "DELETE FROM documentcollection WHERE id=:dcid"), {"dcid": dc_id})
        db.execute(text(
            "DELETE FROM documentbaseline WHERE id=:id"), {"id": baseline_id})
        db.commit()

    def get_acl_filtered_document_collection(self, db: Session, ws: str,
                                               baseline_id: int,
                                               user_login: str = "",
                                               is_admin: bool = False) -> list:
        """获取基线文档集合（ACL 过滤后）。"""
        bl = self.get_baseline(db, ws, baseline_id)
        rows = db.execute(text(
            "SELECT bd.* FROM baselineddocument bd "
            "JOIN documentcollection dc ON bd.documentcollection_id = dc.id "
            "JOIN documentbaseline db ON dc.id = db.documentcollection_id "
            "WHERE db.id = :bid"
        ), {"bid": baseline_id}).fetchall()
        return [{"documentMasterId": r[1], "version": r[2], "iteration": r[3]}
                for r in rows]


document_baseline_service = DocumentBaselineService()
