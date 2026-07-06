"""SimpleWebhookApp — WebhookApp 子类型，dtype=SIMPLE_HTTP。"""
from app.models.workflow import WebhookApp
class SimpleWebhookApp(WebhookApp):
    __mapper_args__ = {"polymorphic_identity": "SIMPLE_HTTP"}
