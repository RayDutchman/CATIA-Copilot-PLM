"""GCMSender——GCM 推送通知发送器。

对齐 Java GCMSenderBean。向 Google Cloud Messaging 发送推送通知。
Python 侧简化实现：记录通知日志，可对接实际推送服务（Firebase/FCM）。
"""
import json
import logging
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class GCMSender:
    """GCM 推送通知服务。"""

    def __init__(self):
        self._api_key = None

    def send_state_notification(self, db: Session, accounts: list,
                                 document_revision) -> None:
        """发送文档状态变更通知。"""
        for account in accounts:
            self._send_notification(account, document_revision, "STATE_CHANGE")

    def send_iteration_notification(self, db: Session, accounts: list,
                                     document_revision) -> None:
        """发送文档迭代更新通知。"""
        for account in accounts:
            self._send_notification(account, document_revision, "ITERATION")

    def send_part_notification(self, db: Session, accounts: list,
                                part_revision, event_type: str = "STATE_CHANGE") -> None:
        """发送零件通知（Java 中没有，Python 扩展）。"""
        for account in accounts:
            self._send_part_notification(account, part_revision, event_type)

    def _send_notification(self, account, document_revision, event_type: str) -> None:
        """发送单条通知。"""
        if not account:
            return

        payload = {
            "workspaceId": document_revision.workspace_id,
            "documentMasterId": document_revision.documentmaster_id,
            "documentMasterVersion": document_revision.version,
            "eventType": event_type,
        }

        gcm_id = getattr(account, 'gcm_id', None)
        if gcm_id:
            logger.info("GCM notification sent: %s → %s", event_type, gcm_id)
            self._send_gcm_message(gcm_id, payload)
        else:
            logger.debug("Skip GCM (no gcm_id): %s", event_type)

    def _send_part_notification(self, account, part_revision, event_type: str) -> None:
        """发送零件相关的推送通知。"""
        if not account:
            return

        payload = {
            "workspaceId": part_revision.workspace_id,
            "partNumber": part_revision.partmaster_partnumber,
            "partVersion": part_revision.version,
            "eventType": event_type,
        }

        gcm_id = getattr(account, 'gcm_id', None)
        if gcm_id:
            logger.info("GCM part notification sent: %s → %s", event_type, gcm_id)
            self._send_gcm_message(gcm_id, payload)

    def _send_gcm_message(self, gcm_id: str, payload: dict) -> None:
        """实际发送 GCM/FCM 消息。

        生产中应通过 Firebase Admin SDK 或 HTTP API 发送。
        当前 Stub：记录日志。
        """
        try:
            import requests
            api_key = self._get_api_key()
            if not api_key:
                logger.warning("GCM API key not configured")
                return

            headers = {
                "Authorization": f"key={api_key}",
                "Content-Type": "application/json",
            }
            body = {
                "to": gcm_id,
                "data": payload,
            }
            resp = requests.post(
                "https://fcm.googleapis.com/fcm/send",
                headers=headers,
                json=body,
                timeout=10,
            )
            if resp.status_code != 200:
                logger.warning("GCM send failed: %s %s", resp.status_code, resp.text)
        except ImportError:
            logger.debug("requests not installed, GCM stub mode")
        except Exception as e:
            logger.error("GCM send error: %s", e)

    def _get_api_key(self) -> str:
        """加载 GCM API Key。"""
        if self._api_key:
            return self._api_key
        import os
        self._api_key = os.getenv("GCM_API_KEY", "")
        return self._api_key


gcm_sender = GCMSender()
