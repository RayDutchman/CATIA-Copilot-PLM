"""SNSWebhookApp — WebhookApp 子类型，dtype=AWS_SNS。"""
from app.models.workflow import WebhookApp
class SNSWebhookApp(WebhookApp):
    __mapper_args__ = {"polymorphic_identity": "AWS_SNS"}
