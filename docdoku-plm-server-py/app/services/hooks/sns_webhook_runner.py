"""SNSWebhookRunner: AWS SNS webhook 执行器。"""
from __future__ import annotations
import json
import logging
from typing import Any

import boto3

from app.services.hooks.webhook_runner import WebhookRunner

logger = logging.getLogger(__name__)


class SNSWebhookRunner(WebhookRunner):
    """对标 Java com.docdoku.plm.server.hooks.SNSWebhookRunner。"""

    def run(self, webhook: Any, login: str, email: str, name: str, subject: str, content: str) -> None:
        app = webhook.webhookApp
        topic_arn = app.topicArn
        aws_account = app.awsAccount
        aws_secret = app.awsSecret
        region = app.region

        try:
            sns = boto3.client(
                "sns",
                region_name=region,
                aws_access_key_id=aws_account,
                aws_secret_access_key=aws_secret,
            )
            message = json.dumps({
                "login": login, "email": email, "name": name,
                "subject": subject, "content": content,
            })
            sns.publish(TopicArn=topic_arn, Message=message)
        except Exception:
            logger.exception("Cannot send notification to SNS service")
