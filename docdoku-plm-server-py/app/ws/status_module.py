"""状态 WebSocket 模块（对标 StatusWebSocketModule + Impl）。

消息类型: USER_STATUS（前端请求查询指定用户在线/离线状态）
对齐 Java StatusWebSocketModuleImpl:252-290
"""
import logging
from fastapi import WebSocket
from app.ws.module import WebSocketModule
from app.ws.message import WSMessage
from app.ws.sessions_manager import ws_sessions

_logger = logging.getLogger(__name__)


class StatusModule(WebSocketModule):

    def can_decode(self, msg: WSMessage) -> bool:
        return msg.type == "USER_STATUS"

    async def process(self, user_login: str, websocket: WebSocket, msg: WSMessage):
        remote_user = msg.get_string("remoteUser")
        if not remote_user:
            return
        if not ws_sessions.is_allowed_to_reach_user(user_login, remote_user):
            return
        is_online = ws_sessions.has_sessions(remote_user)
        status = "USER_STATUS_ONLINE" if is_online else "USER_STATUS_OFFLINE"
        await ws_sessions.send(websocket, {
            "type": "USER_STATUS",
            "remoteUser": remote_user,
            "status": status,
        })


status_module = StatusModule()
