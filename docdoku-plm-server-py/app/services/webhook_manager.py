"""Webhook 管理——对标 Payara WebhookManagerBean。"""
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.workflow import Webhook, WebhookApp
from app.core.exceptions import WebhookNotFoundException


class WebhookService:
    """Webhook 管理服务。"""

    def list_webhooks(self, db: Session, ws: str) -> List[Tuple[Webhook, Optional[WebhookApp]]]:
        hooks = db.query(Webhook).filter(Webhook.workspace_id == ws).all()
        results = []
        for h in hooks:
            app = db.query(WebhookApp).filter(
                WebhookApp.id == h.webhookapp_id).first() if h.webhookapp_id else None
            results.append((h, app))
        return results

    def get_webhook(self, db: Session, ws: str,
                     webhook_id: int) -> Tuple[Webhook, Optional[WebhookApp]]:
        w = db.query(Webhook).filter(
            Webhook.id == webhook_id,
            Webhook.workspace_id == ws).first()
        if not w:
            raise WebhookNotFoundException(
                "WebhookNotFoundException", str(webhook_id))
        app = db.query(WebhookApp).filter(
            WebhookApp.id == w.webhookapp_id).first() if w.webhookapp_id else None
        return (w, app)

    def create_webhook(self, db: Session, ws: str, name: str,
                        active: bool = True,
                        app_data: dict | None = None) -> Tuple[Webhook, WebhookApp]:
        app_data = app_data or {}
        app = WebhookApp(
            dtype=app_data.get("dtype", "SIMPLE_HTTP"),
            uri=app_data.get("uri", ""),
            method=app_data.get("method", "POST"),
            auth=app_data.get("auth"),
            awsaccount=app_data.get("awsAccount"),
            awssecret=app_data.get("awsSecret"),
            region=app_data.get("region"),
            topicarn=app_data.get("topicArn"),
        )
        db.add(app)
        db.flush()
        w = Webhook(
            name=name, workspace_id=ws,
            active=active, webhookapp_id=app.id)
        db.add(w)
        db.commit()
        db.refresh(w)
        db.refresh(app)
        return (w, app)

    def update_webhook(self, db: Session, ws: str, webhook_id: int,
                        data: dict) -> Tuple[Webhook, Optional[WebhookApp]]:
        w, app = self.get_webhook(db, ws, webhook_id)
        if "name" in data:
            w.name = data["name"]
        if "active" in data:
            w.active = data["active"]
        app_data = data.get("webhookApp", {})
        if app_data:
            if app is None:
                app = WebhookApp()
                db.add(app)
                db.flush()
                w.webhookapp_id = app.id
            if "method" in app_data:
                app.method = app_data["method"]
            if "uri" in app_data:
                app.uri = app_data["uri"]
            if "dtype" in app_data:
                app.dtype = app_data["dtype"]
            if "auth" in app_data:
                app.auth = app_data["auth"]
            if "awsAccount" in app_data:
                app.awsaccount = app_data["awsAccount"]
            if "awsSecret" in app_data:
                app.awssecret = app_data["awsSecret"]
            if "region" in app_data:
                app.region = app_data["region"]
            if "topicArn" in app_data:
                app.topicarn = app_data["topicArn"]
        db.commit()
        db.refresh(w)
        if app:
            db.refresh(app)
        return (w, app)

    def delete_webhook(self, db: Session, ws: str, webhook_id: int) -> None:
        w, app = self.get_webhook(db, ws, webhook_id)
        if app:
            db.delete(app)
        db.delete(w)
        db.commit()

    def get_active_webhooks(self, db: Session, ws: str) -> List[Tuple[Webhook, Optional[WebhookApp]]]:
        hooks = db.query(Webhook).filter(
            Webhook.workspace_id == ws,
            Webhook.active.is_(True)).all()
        results = []
        for h in hooks:
            app = db.query(WebhookApp).filter(
                WebhookApp.id == h.webhookapp_id).first() if h.webhookapp_id else None
            results.append((h, app))
        return results

    def configure_simple_webhook(self, db: Session, ws: str,
                                  webhook_id: int, method: str, uri: str,
                                  authorization: str = "") -> Tuple[Webhook, WebhookApp]:
        w, app = self.get_webhook(db, ws, webhook_id)
        if app:
            app.dtype = "SimpleWebhookApp"
            app.method = method
            app.uri = uri
            app.auth = authorization
        else:
            app = WebhookApp(
                dtype="SimpleWebhookApp", method=method,
                uri=uri, auth=authorization)
            db.add(app)
            db.flush()
            w.webhookapp_id = app.id
        db.commit()
        db.refresh(w)
        db.refresh(app)
        return (w, app)

    def configure_sns_webhook(self, db: Session, ws: str,
                               webhook_id: int, topic_arn: str, region: str,
                               aws_account: str,
                               aws_secret: str) -> Tuple[Webhook, WebhookApp]:
        w, app = self.get_webhook(db, ws, webhook_id)
        if app:
            app.dtype = "SNSWebhookApp"
            app.topicarn = topic_arn
            app.region = region
            app.awsaccount = aws_account
            app.awssecret = aws_secret
        else:
            app = WebhookApp(
                dtype="SNSWebhookApp", topicarn=topic_arn,
                region=region, awsaccount=aws_account,
                awssecret=aws_secret)
            db.add(app)
            db.flush()
            w.webhookapp_id = app.id
        db.commit()
        db.refresh(w)
        db.refresh(app)
        return (w, app)


webhook_service = WebhookService()
