"""聊天 WebSocket 模块（对标 ChatWebSocketModule + ChatWebSocketModuleImpl）。

消息类型: CHAT_JOIN / CHAT_LEAVE / CHAT_MESSAGE
房间管理委托给 room.py。
"""
import json
import logging
from fastapi import WebSocket
from app.ws.module import WebSocketModule
from app.ws.message import WSMessage
from app.ws.sessions_manager import ws_sessions
from app.ws.room import room_manager

_logger = logging.getLogger(__name__)

CHAT_TYPES = {"CHAT_JOIN", "CHAT_LEAVE", "CHAT_MESSAGE", "CHAT_USER_LIST"}


class ChatModule(WebSocketModule):

    def can_decode(self, msg: WSMessage) -> bool:
        return msg.type in CHAT_TYPES

    async def process(self, user_login: str, websocket: WebSocket, msg: WSMessage):
        msg_type = msg.type

        if msg_type == "CHAT_JOIN":
            ctx = msg.get_string("context")
            room = room_manager.get_or_create(ctx)
            room.add_session(user_login, websocket)
            # 广播加入事件
            for other in room.get_users():
                if other != user_login:
                    await ws_sessions.broadcast(other, {
                        "type": "CHAT_JOIN", "user": user_login, "context": ctx,
                    })
            await ws_sessions.send(websocket, {
                "type": "CHAT_USER_LIST",
                "users": list(room.get_users()),
            })

        elif msg_type == "CHAT_LEAVE":
            ctx = msg.get_string("context")
            room = room_manager.get_or_create(ctx)
            room.remove_session(user_login, websocket)
            for other in room.get_users():
                if other != user_login:
                    await ws_sessions.broadcast(other, {
                        "type": "CHAT_LEAVE", "user": user_login, "context": ctx,
                    })

        elif msg_type == "CHAT_MESSAGE":
            ctx = msg.get_string("context")
            body = msg.get("message", "")
            room = room_manager.get_or_create(ctx)
            for other in room.get_users():
                if other != user_login:
                    await ws_sessions.broadcast(other, {
                        "type": "CHAT_MESSAGE",
                        "user": user_login,
                        "context": ctx,
                        "message": body,
                    })


chat_module = ChatModule()
