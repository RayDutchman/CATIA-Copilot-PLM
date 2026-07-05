from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from app.models.notification import ModificationNotification
from app.core.exceptions import EntityNotFoundException


class NotificationService:
    def acknowledge(self, db: Session, ws: str, notification_id: int,
                    comment: str, user_login: str) -> ModificationNotification:
        n = db.query(ModificationNotification).filter(
            ModificationNotification.id == notification_id).first()
        if not n:
            raise EntityNotFoundException("ModificationNotificationNotFoundException",
                                          str(notification_id))
        n.acknowledged = True
        n.acknowledgementcomment = comment
        n.acknowledgementdate = datetime.utcnow()
        n.ackauthor_login = user_login
        n.ackauthor_workspace_id = ws
        db.commit()
        db.refresh(n)
        return n

    def list_for_user(self, db: Session, ws: str, login: str) -> list:
        rows = db.execute(text(
            "SELECT * FROM modificationnotification "
            "WHERE impacted_workspace_id = :ws AND acknowledged = false"
        ), {"ws": ws}).fetchall()
        return [self._to_dict(r) for r in rows]

    def _to_dict(self, row) -> dict:
        cols = row._mapping.keys() if hasattr(row, "_mapping") else []
        return {k: row[k] for k in cols}


notification_service = NotificationService()
