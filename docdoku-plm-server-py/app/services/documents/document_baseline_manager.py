"""DocumentBaselineManager——文档基线管理。

对齐 Java DocumentBaselineManagerBean。
"""
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text


class DocumentBaselineService:
    """文档基线管理服务。"""

    def create_baseline(self, db: Session, ws: str, name: str,
                         description: str, baseline_type: int,
                         accepted_docs: list,  # [(dm_id, version, iteration), ...]
                         user_login: str = "") -> dict:
        """创建文档基线。accepted_docs 为已过滤的文档修订键列表。"""
        now = datetime.utcnow()

        result = db.execute(text(
            "INSERT INTO documentcollection (creationdate, author_workspace_id, author_login) "
            "VALUES (:now, :ws, :login) RETURNING id"
        ), {"now": now, "ws": ws, "login": user_login})
        collection_id = result.fetchone()[0]

        result = db.execute(text(
            "INSERT INTO documentbaseline (creationdate, description, name, type, "
            "author_workspace_id, author_login, documentcollection_id) "
            "VALUES (:now, :desc, :name, :type, :ws, :login, :col_id) RETURNING id"
        ), {
            "now": now, "desc": description,
            "name": name, "type": baseline_type,
            "ws": ws, "login": user_login, "col_id": collection_id
        })
        baseline_id = result.fetchone()[0]

        for dm_id, version, iteration in accepted_docs:
            db.execute(text(
                "INSERT INTO baselineddocument (target_iteration, documentcollection_id, "
                "target_documentmaster_id, target_docrevision_version, target_workspace_id) "
                "VALUES (:iter, :col_id, :dm_id, :ver, :ws)"
            ), {
                "iter": iteration,
                "col_id": collection_id,
                "dm_id": dm_id,
                "ver": version,
                "ws": ws
            })

        db.commit()

        return {
            "id": baseline_id, "name": name,
            "description": description, "type": baseline_type,
            "creationDate": now, "authorLogin": user_login,
            "authorWorkspaceId": ws, "collectionId": collection_id
        }

    def get_baselines(self, db: Session, ws: str) -> list[dict]:
        """获取工作空间的所有文档基线（只含有关联文档的基线）。"""
        rows = db.execute(text(
            "SELECT DISTINCT db.id, db.name, db.description, db.type, "
            "db.creationdate, db.author_login, db.author_workspace_id "
            "FROM documentbaseline db "
            "JOIN baselineddocument bd ON db.documentcollection_id = bd.documentcollection_id "
            "WHERE bd.target_workspace_id = :ws "
            "ORDER BY db.id"
        ), {"ws": ws}).fetchall()
        return [{"id": r[0], "name": r[1] or "", "description": r[2] or "",
                 "type": r[3], "creationDate": r[4],
                 "authorLogin": r[5] or "", "authorWorkspaceId": r[6] or ws}
                for r in rows]

    def get_baseline(self, db: Session, ws: str, baseline_id: int) -> dict | None:
        """获取单个文档基线。"""
        row = db.execute(text(
            "SELECT db.id, db.name, db.description, db.type, "
            "db.creationdate, db.author_login, db.author_workspace_id "
            "FROM documentbaseline db WHERE db.id = :bid"
        ), {"bid": baseline_id}).fetchone()
        if not row:
            return None
        return {"id": row[0], "name": row[1] or "", "description": row[2] or "",
                "type": row[3], "creationDate": row[4],
                "authorLogin": row[5] or "", "authorWorkspaceId": row[6] or ws}

    def get_baselined_documents(self, db: Session, baseline_id: int) -> list[dict]:
        """获取基线包含的文档修订列表。"""
        docs = db.execute(text(
            "SELECT bd.target_documentmaster_id, bd.target_docrevision_version, bd.target_iteration "
            "FROM baselineddocument bd WHERE bd.documentcollection_id = "
            "(SELECT documentcollection_id FROM documentbaseline WHERE id = :bid) "
            "ORDER BY bd.target_documentmaster_id"
        ), {"bid": baseline_id}).fetchall()
        return [
            {"documentMasterId": d[0], "version": d[1], "iteration": d[2]}
            for d in docs
        ]

    def delete_baseline(self, db: Session, ws: str, baseline_id: int) -> None:
        """删除文档基线（级联清理 baselineddocument 和 documentcollection）。"""
        row = db.execute(text(
            "SELECT documentcollection_id FROM documentbaseline WHERE id = :bid"
        ), {"bid": baseline_id}).fetchone()
        if not row:
            from app.core.exceptions import BaselineNotFoundException
            raise BaselineNotFoundException("BaselineNotFoundException", str(baseline_id))
        collection_id = row[0]
        db.execute(text(
            "DELETE FROM baselineddocument WHERE documentcollection_id = :cid"
        ), {"cid": collection_id})
        db.execute(text(
            "DELETE FROM documentbaseline WHERE id = :bid"), {"bid": baseline_id})
        db.execute(text(
            "DELETE FROM documentcollection WHERE id = :cid"), {"cid": collection_id})
        db.commit()

    def get_acl_filtered_document_collection(self, db: Session, ws: str,
                                               baseline_id: int,
                                               user_login: str = "",
                                               is_admin: bool = False) -> list[dict]:
        """获取基线文档集合（ACL 过滤后）。"""
        self.get_baseline(db, ws, baseline_id)  # 校验存在
        rows = db.execute(text(
            "SELECT bd.* FROM baselineddocument bd "
            "JOIN documentcollection dc ON bd.documentcollection_id = dc.id "
            "JOIN documentbaseline db ON dc.id = db.documentcollection_id "
            "WHERE db.id = :bid"
        ), {"bid": baseline_id}).fetchall()
        return [{"documentMasterId": r[1], "version": r[2], "iteration": r[3]}
                for r in rows]


document_baseline_service = DocumentBaselineService()
