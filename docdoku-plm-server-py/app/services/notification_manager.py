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
        """列出用户未读通知，按 ackauthor_login 过滤以避免跨用户泄漏。"""
        return db.query(ModificationNotification).filter(
            ModificationNotification.impacted_workspace_id == ws,
            ModificationNotification.acknowledged == False,
            ModificationNotification.ackauthor_login == login,
        ).all()

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

    def subscribe_iteration_change(self, db: Session, ws: str, doc_id: str,
                                     ver: str, user_login: str):
        """订阅文档迭代变更通知。"""
        db.execute(text(
            "INSERT INTO iterationchangesubscription "
            "(documentmaster_id, documentrevision_version, documentmaster_workspace_id, "
            "subscriber_login, subscriber_workspace_id) "
            "VALUES (:did, :ver, :ws, :login, :sws) "
            "ON CONFLICT (documentmaster_id, documentrevision_version, "
            "documentmaster_workspace_id, subscriber_login, subscriber_workspace_id) "
            "DO NOTHING"),
            {"did": doc_id, "ver": ver, "ws": ws, "login": user_login, "sws": ws})
        db.commit()

    def unsubscribe_iteration_change(self, db: Session, ws: str, doc_id: str,
                                       ver: str, user_login: str):
        """取消文档迭代变更通知订阅。"""
        db.execute(text(
            "DELETE FROM iterationchangesubscription "
            "WHERE documentmaster_id=:did AND documentrevision_version=:ver "
            "AND documentmaster_workspace_id=:ws AND subscriber_login=:login "
            "AND subscriber_workspace_id=:sws"),
            {"did": doc_id, "ver": ver, "ws": ws, "login": user_login, "sws": ws})
        db.commit()

    def subscribe_state_change(self, db: Session, ws: str, doc_id: str,
                                 ver: str, user_login: str):
        """订阅文档状态变更通知。"""
        db.execute(text(
            "INSERT INTO statechangesubscription "
            "(documentmaster_id, documentrevision_version, documentmaster_workspace_id, "
            "subscriber_login, subscriber_workspace_id) "
            "VALUES (:did, :ver, :ws, :login, :sws) "
            "ON CONFLICT (documentmaster_id, documentrevision_version, "
            "documentmaster_workspace_id, subscriber_login, subscriber_workspace_id) "
            "DO NOTHING"),
            {"did": doc_id, "ver": ver, "ws": ws, "login": user_login, "sws": ws})
        db.commit()

    def unsubscribe_state_change(self, db: Session, ws: str, doc_id: str,
                                   ver: str, user_login: str):
        """取消文档状态变更通知订阅。"""
        db.execute(text(
            "DELETE FROM statechangesubscription "
            "WHERE documentmaster_id=:did AND documentrevision_version=:ver "
            "AND documentmaster_workspace_id=:ws AND subscriber_login=:login "
            "AND subscriber_workspace_id=:sws"),
            {"did": doc_id, "ver": ver, "ws": ws, "login": user_login, "sws": ws})
        db.commit()

    def build_notification_dto(self, n, db: Session) -> dict:
        """构建完整 ModificationNotificationDTO 响应（把 router 层内联 DB 迁入）。"""
        result = {
            "id": n.id,
            "acknowledged": n.acknowledged,
            "impactedPartNumber": n.impacted_partmaster_partnumber,
            "impactedPartVersion": n.impacted_partrevision_version,
            "modifiedPartNumber": n.modified_partmaster_partnumber,
            "modifiedPartVersion": n.modified_partrevision_version,
            "modifiedPartIteration": n.modified_iteration or 0,
            "ackComment": n.acknowledgementcomment or "",
            "ackAuthor": {},
            "author": {},
        }
        if n.acknowledgementdate:
            result["ackDate"] = int(n.acknowledgementdate.timestamp() * 1000)
        else:
            result["ackDate"] = None
        if n.ackauthor_login:
            ack = db.execute(text(
                "SELECT login, name, email FROM account WHERE login = :l"
            ), {"l": n.ackauthor_login}).fetchone()
            result["ackAuthor"] = {"login": ack[0], "name": ack[1], "email": ack[2]} if ack else {"login": n.ackauthor_login}
        else:
            result["ackAuthor"] = {}

        if n.modified_workspace_id and n.modified_partmaster_partnumber:
            pm = db.execute(text(
                "SELECT name FROM partmaster WHERE partnumber = :pn AND workspace_id = :ws"
            ), {"pn": n.modified_partmaster_partnumber, "ws": n.modified_workspace_id}).fetchone()
            result["modifiedPartName"] = pm[0] if pm else None
            pi = db.execute(text(
                "SELECT author_login, checkindate, iterationnote FROM partiteration "
                "WHERE workspace_id = :ws AND partmaster_partnumber = :pn "
                "AND partrevision_version = :v AND iteration = :iter"
            ), {
                "ws": n.modified_workspace_id,
                "pn": n.modified_partmaster_partnumber,
                "v": n.modified_partrevision_version,
                "iter": n.modified_iteration,
            }).fetchone()
            if pi:
                author_login = pi[0]
                checkindate = pi[1]
                iteration_note = pi[2]
                if author_login:
                    au = db.execute(text(
                        "SELECT login, name, email FROM account WHERE login = :l"
                    ), {"l": author_login}).fetchone()
                    result["author"] = {"login": au[0], "name": au[1], "email": au[2]} if au else {"login": author_login}
                else:
                    result["author"] = {}
                result["checkInDate"] = int(checkindate.timestamp() * 1000) if checkindate else None
                result["iterationNote"] = iteration_note or ""
            else:
                result["author"] = {}
                result["checkInDate"] = None
                result["iterationNote"] = ""
        else:
            result["modifiedPartName"] = None
            result["author"] = {}
            result["checkInDate"] = None
            result["iterationNote"] = ""
        return result

    def _to_dict(self, row) -> dict:
        cols = row._mapping.keys() if hasattr(row, "_mapping") else []
        return {k: row[k] for k in cols}


notification_service = NotificationService()
