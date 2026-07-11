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
        # webhookapp 单表继承，dtype 判别符 = 'SimpleWebhookApp'；webhook.webhookapp_id 关联
        wh = db.execute(text(
            "SELECT webhookapp_id FROM webhook WHERE id = :id AND workspace_id = :ws"
        ), {"id": webhook_id, "ws": ws}).first()
        app_id = wh[0] if wh else None
        if app_id:
            db.execute(text(
                "UPDATE webhookapp SET dtype = 'SimpleWebhookApp', method = :m, "
                "uri = :u, auth = :a WHERE id = :aid"
            ), {"m": method, "u": uri, "a": authorization, "aid": app_id})
        else:
            result = db.execute(text(
                "INSERT INTO webhookapp (dtype, method, uri, auth) "
                "VALUES ('SimpleWebhookApp', :m, :u, :a) RETURNING id"
            ), {"m": method, "u": uri, "a": authorization})
            app_id = result.fetchone()[0]
            db.execute(text(
                "UPDATE webhook SET webhookapp_id = :aid WHERE id = :id AND workspace_id = :ws"
            ), {"aid": app_id, "id": webhook_id, "ws": ws})
        db.commit()
        return {"type": "simple", "webhookId": webhook_id, "method": method, "uri": uri}

    def configure_sns_webhook(self, db: Session, ws: str,
                               webhook_id: int, topic_arn: str, region: str,
                               aws_account: str, aws_secret: str) -> dict:
        wh = db.execute(text(
            "SELECT webhookapp_id FROM webhook WHERE id = :id AND workspace_id = :ws"
        ), {"id": webhook_id, "ws": ws}).first()
        app_id = wh[0] if wh else None
        if app_id:
            db.execute(text(
                "UPDATE webhookapp SET dtype = 'SNSWebhookApp', topicarn = :ta, region = :r, "
                "awsaccount = :aa, awssecret = :asec WHERE id = :aid"
            ), {"ta": topic_arn, "r": region, "aa": aws_account,
                "asec": aws_secret, "aid": app_id})
        else:
            result = db.execute(text(
                "INSERT INTO webhookapp (dtype, topicarn, region, awsaccount, awssecret) "
                "VALUES ('SNSWebhookApp', :ta, :r, :aa, :asec) RETURNING id"
            ), {"ta": topic_arn, "r": region, "aa": aws_account, "asec": aws_secret})
            app_id = result.fetchone()[0]
            db.execute(text(
                "UPDATE webhook SET webhookapp_id = :aid WHERE id = :id AND workspace_id = :ws"
            ), {"aid": app_id, "id": webhook_id, "ws": ws})
        db.commit()
        return {"type": "sns", "webhookId": webhook_id, "topicArn": topic_arn, "region": region}


webhook_service = WebhookService()
