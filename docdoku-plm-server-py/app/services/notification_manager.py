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
        """订阅标签变更事件。event 含 'STATE' → onstatechange，否则 oniterationchange。"""
        on_state = "STATE" in (event or "").upper()
        on_iter = not on_state
        existing = db.execute(text(
            "SELECT oniterationchange, onstatechange FROM tagusersubscription "
            "WHERE tag_label = :t AND tag_workspace_id = :ws "
            "AND subscriber_login = :l AND subscriber_workspace_id = :ws"
        ), {"t": tag_label, "ws": ws, "l": user_login}).first()
        if existing:
            db.execute(text(
                "UPDATE tagusersubscription SET oniterationchange = :oi, onstatechange = :os "
                "WHERE tag_label = :t AND tag_workspace_id = :ws "
                "AND subscriber_login = :l AND subscriber_workspace_id = :ws"
            ), {"t": tag_label, "ws": ws, "l": user_login,
                "oi": on_iter or existing[0], "os": on_state or existing[1]})
        else:
            db.execute(text(
                "INSERT INTO tagusersubscription "
                "(tag_label, tag_workspace_id, subscriber_login, subscriber_workspace_id, "
                "oniterationchange, onstatechange) "
                "VALUES (:t, :ws, :l, :ws, :oi, :os)"
            ), {"t": tag_label, "ws": ws, "l": user_login, "oi": on_iter, "os": on_state})
        db.commit()

    def unsubscribe_from_tag_event(self, db: Session, ws: str, tag_label: str,
                                    user_login: str, event: str):
        """取消标签变更事件订阅。"""
        db.execute(text(
            "DELETE FROM tagusersubscription "
            "WHERE tag_label = :t AND tag_workspace_id = :ws "
            "AND subscriber_login = :l AND subscriber_workspace_id = :ws"
        ), {"t": tag_label, "ws": ws, "l": user_login})
        db.commit()

    def list_tag_subscriptions(self, db: Session, ws: str, user_login: str) -> list:
        """列出用户的标签订阅。"""
        rows = db.execute(text(
            "SELECT tag_label, oniterationchange, onstatechange FROM tagusersubscription "
            "WHERE tag_workspace_id = :ws AND subscriber_login = :l"
        ), {"ws": ws, "l": user_login}).fetchall()
        return [{"tag": r[0], "onIterationChange": r[1], "onStateChange": r[2],
                 "workspaceId": ws} for r in rows]

    def list_tag_subscriptions_for_tag(self, db: Session, ws: str,
                                        tag_label: str) -> list:
        """列出指定标签的所有订阅者。"""
        rows = db.execute(text(
            "SELECT subscriber_login, oniterationchange, onstatechange FROM tagusersubscription "
            "WHERE tag_workspace_id = :ws AND tag_label = :t"
        ), {"ws": ws, "t": tag_label}).fetchall()
        return [{"login": r[0], "onIterationChange": r[1], "onStateChange": r[2],
                 "workspaceId": ws} for r in rows]

    def _to_dict(self, row) -> dict:
        cols = row._mapping.keys() if hasattr(row, "_mapping") else []
        return {k: row[k] for k in cols}


notification_service = NotificationService()
