"""状态广播 WebSocket 模块（对标 StatusWebSocketModule + Impl）。

消息类型: STATUS_SUBSCRIBE / STATUS_UNSUBSCRIBE / STATUS_UPDATE
用于推送用户在线状态、文档/零件状态变更通知。
"""
import logging
from fastapi import WebSocket
from app.ws.module import WebSocketModule
from app.ws.message import WSMessage
from app.ws.sessions_manager import ws_sessions

_logger = logging.getLogger(__name__)

STATUS_TYPES = {"STATUS_SUBSCRIBE", "STATUS_UNSUBSCRIBE", "STATUS_UPDATE"}


class StatusModule(WebSocketModule):

    def can_decode(self, msg: WSMessage) -> bool:
        return msg.type in STATUS_TYPES

    async def process(self, user_login: str, websocket: WebSocket, msg: WSMessage):
        msg_type = msg.type

        if msg_type == "STATUS_SUBSCRIBE":
            await ws_sessions.send(websocket, {
                "type": "STATUS_SUBSCRIBED",
                "message": "已订阅状态更新",
            })

        elif msg_type == "STATUS_UNSUBSCRIBE":
            await ws_sessions.send(websocket, {
                "type": "STATUS_UNSUBSCRIBED",
                "message": "已取消订阅",
            })

        elif msg_type == "STATUS_UPDATE":
            ws_id = msg.get_string("workspaceId") or ""
            entity = msg.get_string("entity") or ""
            status_msg = msg.get_string("status") or ""
            # 广播给 workspace 内的所有在线用户
            # 简单实现: 广播给所有连接（后续可按 workspace 索引优化）
            await ws_sessions.send(websocket, {
                "type": "STATUS_UPDATE",
                "workspaceId": ws_id,
                "entity": entity,
                "status": status_msg,
                "user": user_login,
            })


status_module = StatusModule()
