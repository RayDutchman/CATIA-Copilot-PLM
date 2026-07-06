"""SimpleWebhookRunner: HTTP webhook 执行器。"""
from __future__ import annotations
import json
import logging
from typing import Any

import httpx

from app.services.hooks.webhook_runner import WebhookRunner

logger = logging.getLogger(__name__)


class SimpleWebhookRunner(WebhookRunner):
    """对标 Java com.docdoku.plm.server.hooks.SimpleWebhookRunner。"""

    def run(self, webhook: Any, login: str, email: str, name: str, subject: str, content: str) -> None:
        app = webhook.webhookApp
        method = app.method.upper()
        uri = app.uri
        authorization = app.authorization

        payload = {
            "login": login, "email": email, "name": name,
            "subject": subject, "content": content,
        }

        try:
            headers = {"authorization": authorization} if authorization else {}
            if method == "POST":
                response = httpx.post(uri, json=payload, headers=headers)
            elif method == "PUT":
                response = httpx.put(uri, json=payload, headers=headers)
            elif method == "GET":
                response = httpx.get(uri, params=payload, headers=headers)
            else:
                logger.error("Unsupported method %s", method)
                return
            logger.info("Webhook response status %s: %s", response.status_code, response.text[:200])
        except Exception:
            logger.exception("Webhook runner failed")
