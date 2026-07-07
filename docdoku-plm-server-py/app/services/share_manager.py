"""共享管理——对标 Payara ShareManagerBean。

管理文档/零件的公开共享链接。
"""
from sqlalchemy.orm import Session
from sqlalchemy import text


class ShareService:
    """共享链接管理服务。"""

    def find_shared_entity(self, db: Session, uuid: str) -> dict:
        """通过 UUID 查找共享实体。"""
        row = db.execute(text(
            "SELECT se.* FROM sharedentity se WHERE se.password = :uuid"
        ), {"uuid": uuid}).first()
        if not row:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("SharedEntityNotFoundException", uuid)
        return dict(row._mapping)

    def delete_shared_entity_if_expired(self, db: Session, uuid: str) -> bool:
        """删除已过期的共享链接。"""
        row = db.execute(text(
            "SELECT expire FROM sharedentity WHERE password = :uuid"
        ), {"uuid": uuid}).first()
        if not row:
            return False
        expire = row[0]
        if expire:
            from datetime import datetime
            if expire > datetime.utcnow():
                return False  # 未过期
        db.execute(text(
            "DELETE FROM sharedentity WHERE password = :uuid"
        ), {"uuid": uuid})
        db.commit()
        return True


share_service = ShareService()
