"""WebhookRunner: CDI webhook 执行接口。"""
from abc import ABC, abstractmethod


class WebhookRunner(ABC):
    """对标 Java com.docdoku.plm.server.hooks.WebhookRunner 接口。"""

    @abstractmethod
    def run(self, webhook, login: str, email: str, name: str, subject: str, content: str) -> None:
        ...
