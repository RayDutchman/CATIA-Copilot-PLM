"""共享管理——对标 Payara ShareManagerBean。

管理文档/零件的公开共享链接。"""
import hashlib
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text


class ShareService:
    """共享链接管理服务。"""

    def find_shared_entity(self, db: Session, uuid: str) -> dict:
        """通过 UUID 查找共享实体（返回 dict，保持向后兼容）。"""
        row = db.execute(text(
            "SELECT se.* FROM sharedentity se WHERE se.uuid = :uuid"
        ), {"uuid": uuid}).first()
        if not row:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("SharedEntityNotFoundException", uuid)
        return dict(row._mapping)

    def delete_shared_entity_if_expired(self, db: Session, uuid: str) -> bool:
        """删除已过期的共享链接。返回 True 表示已删除。"""
        row = db.execute(text(
            "SELECT expiredate FROM sharedentity WHERE uuid = :uuid"
        ), {"uuid": uuid}).first()
        if not row:
            return False
        expire = row[0]
        if expire:
            if expire > datetime.utcnow():
                return False  # 未过期
        db.execute(text(
            "DELETE FROM sharedentity WHERE uuid = :uuid"
        ), {"uuid": uuid})
        db.commit()
        return True

    # ========== 新增方法（Batch 2 Subagent C）==========

    def get_shared_entity(self, db: Session, uuid: str, password: str | None = None):
        """获取共享实体，含密码校验和过期检查（自动删除过期的）。

        Returns:
            SQLAlchemy Row 对象

        Raises:
            SharedEntityNotFoundException: UUID 不存在
            SharedEntityPasswordRequiredException: 密码保护且未提供或密码错误
            SharedEntityExpiredException: 共享链接已过期
        """
        entity = db.execute(text(
            "SELECT uuid, dtype, entity_workspace_id, password, expiredate, "
            "partmaster_partnumber, partrevision_version, "
            "documentmaster_id, documentrevision_version "
            "FROM sharedentity WHERE uuid = :uuid"
        ), {"uuid": uuid}).fetchone()

        if not entity:
            from app.core.exceptions import SharedEntityNotFoundException
            raise SharedEntityNotFoundException("SharedEntityNotFoundException", uuid)

        if entity.password is not None:
            if password is None or hashlib.md5(password.encode()).hexdigest() != entity.password:
                from app.core.exceptions import SharedEntityPasswordRequiredException
                raise SharedEntityPasswordRequiredException("SharedEntityNotFoundException", uuid)

        if entity.expiredate is not None:
            now = datetime.now(timezone.utc)
            expire = entity.expiredate.replace(tzinfo=timezone.utc) if entity.expiredate.tzinfo is None else entity.expiredate
            if expire < now:
                db.execute(text("DELETE FROM sharedentity WHERE uuid = :uuid"), {"uuid": uuid})
                db.commit()
                from app.core.exceptions import SharedEntityExpiredException
                raise SharedEntityExpiredException("SharedEntityNotFoundException", uuid)

        return entity

    def get_shared_document_row(self, db: Session, entity):
        """根据共享实体查询文档详情（documentrevision JOIN documentmaster）。

        Args:
            entity: get_shared_entity() 返回的 Row，含 entity_workspace_id、documentmaster_id、documentrevision_version

        Returns:
            Row 或 None
        """
        return db.execute(text(
            "SELECT d.title, d.description, d.status, d.author_login, d.creationdate, "
            "dm.type, d.version, dm.id AS documentmaster_id, d.workspace_id "
            "FROM documentrevision d "
            "JOIN documentmaster dm ON dm.workspace_id = d.workspace_id "
            "AND dm.id = d.documentmaster_id "
            "WHERE d.workspace_id = :ws AND d.documentmaster_id = :dmid "
            "AND d.version = :ver"
        ), {
            "ws": entity.entity_workspace_id,
            "dmid": entity.documentmaster_id,
            "ver": entity.documentrevision_version,
        }).fetchone()

    def get_shared_part_row(self, db: Session, entity):
        """根据共享实体查询零件详情（partrevision JOIN partmaster）。

        Args:
            entity: get_shared_entity() 返回的 Row，含 entity_workspace_id、partmaster_partnumber、partrevision_version

        Returns:
            Row 或 None
        """
        return db.execute(text(
            "SELECT pr.description, pr.status, pr.author_login, pr.creationdate, "
            "pm.type, pm.name, pm.partnumber, pr.version, pr.workspace_id "
            "FROM partrevision pr "
            "JOIN partmaster pm ON pm.workspace_id = pr.workspace_id "
            "AND pm.partnumber = pr.partmaster_partnumber "
            "WHERE pr.workspace_id = :ws AND pr.partmaster_partnumber = :pn "
            "AND pr.version = :ver"
        ), {
            "ws": entity.entity_workspace_id,
            "pn": entity.partmaster_partnumber,
            "ver": entity.partrevision_version,
        }).fetchone()

    def get_document_revision(self, db: Session, workspace_id: str, doc_id: str, version: str):
        """查询文档版本（用于 public_shared 路径）。

        Returns:
            DocumentRevision ORM 对象 或 None
        """
        from app.models.document import DocumentRevision
        return db.query(DocumentRevision).filter(
            DocumentRevision.workspace_id == workspace_id,
            DocumentRevision.documentmaster_id == doc_id,
            DocumentRevision.version == version,
        ).first()

    def get_part_revision(self, db: Session, workspace_id: str, part_number: str, version: str):
        """查询零件版本（用于 public_shared 路径）。

        Returns:
            PartRevision ORM 对象 或 None
        """
        from app.models.part import PartRevision
        return db.query(PartRevision).filter(
            PartRevision.workspace_id == workspace_id,
            PartRevision.partmaster_partnumber == part_number,
            PartRevision.version == version,
        ).first()

    def check_workspace_member(self, db: Session, login: str, workspace_id: str):
        """验证工作区启用且用户是成员。

        Raises:
            WorkspaceNotFoundException: 工作区不存在
            WorkspaceNotEnabledException: 工作区未启用
            EntityNotFoundException: 用户非成员
        """
        row = db.execute(text(
            "SELECT enabled FROM workspace WHERE id = :w"
        ), {"w": workspace_id}).first()
        if not row:
            from app.core.exceptions import WorkspaceNotFoundException
            raise WorkspaceNotFoundException("WorkspaceNotFoundException", workspace_id)
        if not bool(row[0]):
            from app.core.exceptions import WorkspaceNotEnabledException
            raise WorkspaceNotEnabledException("WorkspaceNotEnabledException", workspace_id)
        member = db.execute(text(
            "SELECT 1 FROM userdata WHERE login=:l AND workspace_id=:w"
        ), {"l": login, "w": workspace_id}).first()
        if not member:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("UserNotFoundException", login)

    def get_account_info(self, db: Session, login: str) -> dict:
        """获取账户信息，用于构建 author DTO。

        Returns:
            {"login": str, "name": str, "email": str|None, "language": str|None}
        """
        from app.models.auth import Account
        acc = db.query(Account).filter(Account.login == login).first()
        return {
            "login": login,
            "name": acc.name if acc else login,
            "email": acc.email if acc else None,
            "language": acc.language if acc else None,
        }


share_service = ShareService()
