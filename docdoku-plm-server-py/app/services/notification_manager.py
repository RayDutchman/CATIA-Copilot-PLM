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

    # ========== Tag 订阅管理（P1 stubs） ==========

    def subscribe_to_tag_event(self, db: Session, ws: str, tag_label: str,
                                user_login: str, event: str):
        """订阅标签变更事件（stub）。"""
        existing = db.execute(text(
            "SELECT 1 FROM tagsubscription "
            "WHERE tag_label = :t AND workspace_id = :ws "
            "AND subscriber_login = :l AND event = :e"
        ), {"t": tag_label, "ws": ws, "l": user_login, "e": event}).first()
        if existing:
            return
        db.execute(text(
            "INSERT INTO tagsubscription "
            "(tag_label, workspace_id, subscriber_login, subscriber_workspace_id, event) "
            "VALUES (:t, :ws, :l, :ws2, :e)"
        ), {"t": tag_label, "ws": ws, "l": user_login, "ws2": ws, "e": event})
        db.commit()

    def unsubscribe_from_tag_event(self, db: Session, ws: str, tag_label: str,
                                    user_login: str, event: str):
        """取消标签变更事件订阅（stub）。"""
        db.execute(text(
            "DELETE FROM tagsubscription "
            "WHERE tag_label = :t AND workspace_id = :ws "
            "AND subscriber_login = :l AND event = :e"
        ), {"t": tag_label, "ws": ws, "l": user_login, "e": event})
        db.commit()

    def list_tag_subscriptions(self, db: Session, ws: str, user_login: str) -> list:
        """列出用户的标签订阅（stub）。"""
        rows = db.execute(text(
            "SELECT tag_label, event FROM tagsubscription "
            "WHERE workspace_id = :ws AND subscriber_login = :l"
        ), {"ws": ws, "l": user_login}).fetchall()
        return [{"tag": r[0], "event": r[1], "workspaceId": ws} for r in rows]

    def list_tag_subscriptions_for_tag(self, db: Session, ws: str,
                                        tag_label: str) -> list:
        """列出指定标签的所有订阅者（stub）。"""
        rows = db.execute(text(
            "SELECT subscriber_login, event FROM tagsubscription "
            "WHERE workspace_id = :ws AND tag_label = :t"
        ), {"ws": ws, "t": tag_label}).fetchall()
        return [{"login": r[0], "event": r[1], "workspaceId": ws} for r in rows]

    def _to_dict(self, row) -> dict:
        cols = row._mapping.keys() if hasattr(row, "_mapping") else []
        return {k: row[k] for k in cols}


notification_service = NotificationService()
