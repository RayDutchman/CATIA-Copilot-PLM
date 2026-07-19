"""聊天 WebSocket 模块（对标 ChatWebSocketModule + Impl）。

消息类型: CHAT_MESSAGE（前端直接发送点对点消息，不需要先 JOIN room）。
对齐 Java ChatWebSocketModuleImpl:325-393

前端期望：CHAT_MESSAGE 含 remoteUser/context/message/sender
→ 后端回复 CHAT_MESSAGE_ACK 给发送者，转发 CHAT_MESSAGE 给接收者
→ 接收者离线 → 回复 CHAT_MESSAGE UNREACHABLE
"""
import logging
from fastapi import WebSocket
from app.ws.module import WebSocketModule
from app.ws.message import WSMessage
from app.ws.sessions_manager import ws_sessions

_logger = logging.getLogger(__name__)

CHAT_TYPES = {"CHAT_MESSAGE"}


class ChatModule(WebSocketModule):

    def can_decode(self, msg: WSMessage) -> bool:
        return msg.type in CHAT_TYPES

    async def process(self, user_login: str, websocket: WebSocket, msg: WSMessage):
        remote_user = msg.get_string("remoteUser")
        context = msg.get_string("context") or ""
        message = msg.get("message", "")
        sender = msg.get_string("sender") or user_login

        if not remote_user:
            return
        if not ws_sessions.is_allowed_to_reach_user(user_login, remote_user):
            return

        if not ws_sessions.has_sessions(remote_user):
            await ws_sessions.send(websocket, {
                "type": "CHAT_MESSAGE",
                "remoteUser": remote_user,
                "sender": "",
                "message": "",
                "context": context,
                "error": "UNREACHABLE",
            })
            return

        ack = {
            "type": "CHAT_MESSAGE_ACK",
            "remoteUser": remote_user,
            "sender": sender,
            "message": message,
            "context": context,
            "error": "",
        }
        forwarded = {
            "type": "CHAT_MESSAGE",
            "remoteUser": sender,
            "sender": sender,
            "message": message,
            "context": context,
            "error": "",
        }
        await ws_sessions.broadcast(user_login, ack)
        await ws_sessions.broadcast(remote_user, forwarded)


chat_module = ChatModule()
