"""Webhook 管理——对标 Payara WebhookManagerBean。

管理 Webhook 的 CRUD 和配置。
"""
from sqlalchemy.orm import Session
from sqlalchemy import text


class WebhookService:
    """Webhook 管理服务。"""

    def create_webhook(self, db: Session, ws: str, name: str,
                        active: bool = True) -> dict:
        result = db.execute(text(
            "INSERT INTO webhook (workspace_id, name, active) "
            "VALUES (:ws, :n, :a) RETURNING id"
        ), {"ws": ws, "n": name, "a": active})
        wid = result.fetchone()[0]
        db.commit()
        return {"id": wid, "workspaceId": ws, "name": name, "active": active}

    def get_webhooks(self, db: Session, ws: str) -> list:
        rows = db.execute(text(
            "SELECT * FROM webhook WHERE workspace_id = :ws"
        ), {"ws": ws}).fetchall()
        return [dict(r._mapping) for r in rows]

    def get_webhook(self, db: Session, ws: str, webhook_id: int) -> dict:
        row = db.execute(text(
            "SELECT * FROM webhook WHERE workspace_id = :ws AND id = :id"
        ), {"ws": ws, "id": webhook_id}).first()
        if not row:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("WebhookNotFoundException", str(webhook_id))
        return dict(row._mapping)

    def update_webhook(self, db: Session, ws: str, webhook_id: int,
                        name: str, active: bool) -> dict:
        db.execute(text(
            "UPDATE webhook SET name = :n, active = :a "
            "WHERE workspace_id = :ws AND id = :id"
        ), {"n": name, "a": active, "ws": ws, "id": webhook_id})
        db.commit()
        return self.get_webhook(db, ws, webhook_id)

    def delete_webhook(self, db: Session, ws: str, webhook_id: int) -> None:
        db.execute(text(
            "DELETE FROM webhook WHERE workspace_id = :ws AND id = :id"
        ), {"ws": ws, "id": webhook_id})
        db.commit()

    def get_active_webhooks(self, db: Session, ws: str) -> list:
        rows = db.execute(text(
            "SELECT * FROM webhook WHERE workspace_id = :ws AND active = true"
        ), {"ws": ws}).fetchall()
        return [dict(r._mapping) for r in rows]

    def configure_simple_webhook(self, db: Session, ws: str,
                                  webhook_id: int, method: str, uri: str,
                                  authorization: str = "") -> dict:
        db.execute(text(
            "INSERT INTO simplewebhookapp (webhook_id, method, uri, authorization) "
            "VALUES (:wid, :m, :u, :a) "
            "ON CONFLICT (webhook_id) DO UPDATE SET method = :m2, uri = :u2, authorization = :a2"
        ), {"wid": webhook_id, "m": method, "u": uri, "a": authorization,
            "m2": method, "u2": uri, "a2": authorization})
        db.commit()
        return {"type": "simple", "webhookId": webhook_id, "method": method, "uri": uri}

    def configure_sns_webhook(self, db: Session, ws: str,
                               webhook_id: int, topic_arn: str, region: str,
                               aws_account: str, aws_secret: str) -> dict:
        db.execute(text(
            "INSERT INTO snswebhookapp (webhook_id, topicarn, region, awsaccount, awssecret) "
            "VALUES (:wid, :ta, :r, :aa, :as) "
            "ON CONFLICT (webhook_id) DO UPDATE SET "
            "topicarn = :ta2, region = :r2, awsaccount = :aa2, awssecret = :as2"
        ), {"wid": webhook_id, "ta": topic_arn, "r": region,
            "aa": aws_account, "as": aws_secret,
            "ta2": topic_arn, "r2": region, "aa2": aws_account, "as2": aws_secret})
        db.commit()
        return {"type": "sns", "webhookId": webhook_id, "topicArn": topic_arn, "region": region}


webhook_service = WebhookService()
