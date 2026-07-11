"""公开实体管理——对标 Payara PublicEntityManagerBean。

提供无需认证的公开文件/实体访问。
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.exceptions import FileNotFoundException


class PublicEntityService:
    """公开实体访问服务。"""

    def get_public_part_revision(self, db: Session, ws: str,
                                  part_number: str, version: str) -> dict:
        row = db.execute(text(
            "SELECT pr.* FROM partrevision pr "
            "WHERE pr.workspace_id = :ws AND pr.partmaster_partnumber = :pn "
            "AND pr.version = :v"
        ), {"ws": ws, "pn": part_number, "v": version}).first()
        if not row:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("PartRevisionNotFoundException",
                                           part_number, version)
        return dict(row._mapping)

    def get_public_document_revision(self, db: Session, ws: str,
                                      document_id: str, version: str) -> dict:
        row = db.execute(text(
            "SELECT dr.* FROM documentrevision dr "
            "WHERE dr.workspace_id = :ws AND dr.documentmaster_id = :dm "
            "AND dr.version = :v"
        ), {"ws": ws, "dm": document_id, "v": version}).first()
        if not row:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("DocumentRevisionNotFoundException",
                                           document_id, version)
        return dict(row._mapping)

    def can_access_part(self, db: Session, ws: str,
                         part_number: str, version: str,
                         iteration: int) -> bool:
        row = db.execute(text(
            "SELECT 1 FROM partiteration "
            "WHERE workspace_id = :ws AND partmaster_partnumber = :pn "
            "AND partrevision_version = :v AND iteration = :i"
        ), {"ws": ws, "pn": part_number, "v": version, "i": iteration}).first()
        return row is not None

    def can_access_document(self, db: Session, ws: str,
                             document_id: str, version: str,
                             iteration: int) -> bool:
        row = db.execute(text(
            "SELECT 1 FROM documentiteration "
            "WHERE workspace_id = :ws AND documentmaster_id = :dm "
            "AND documentrevision_version = :v AND iteration = :i"
        ), {"ws": ws, "dm": document_id, "v": version, "i": iteration}).first()
        return row is not None

    def get_binary_resource(self, db: Session, full_name: str) -> dict:
        """通过 fullName 查找 BinaryResource（公开访问）。"""
        row = db.execute(text(
            "SELECT * FROM binaryresource WHERE fullname = :fn"
        ), {"fn": full_name}).first()
        if row:
            return dict(row._mapping)
        raise FileNotFoundException("FileNotFoundException", full_name)


public_entity_service = PublicEntityService()
