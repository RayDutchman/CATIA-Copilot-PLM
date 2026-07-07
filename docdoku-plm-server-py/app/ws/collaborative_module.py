"""协同 WebSocket 模块（对标 CollaborativeWebSocketModule + Impl + CollaborativeRoom）。

消息类型: COLLAB_JOIN / COLLAB_LEAVE / COLLAB_MOUSE / COLLAB_CAMERA / COLLAB_SELECTION
用于多用户实时协同浏览 3D 场景。
"""
import json
import logging
from fastapi import WebSocket
from app.ws.module import WebSocketModule
from app.ws.message import WSMessage
from app.ws.sessions_manager import ws_sessions
from app.ws.room import room_manager

_logger = logging.getLogger(__name__)

COLLAB_TYPES = {
    "COLLAB_JOIN", "COLLAB_LEAVE", "COLLAB_MOUSE",
    "COLLAB_CAMERA", "COLLAB_SELECTION", "COLLAB_MARKER",
}


class CollaborativeModule(WebSocketModule):
    """协同浏览模块。

    处理多用户实时协同操作：鼠标位置/相机变换/选中/标注。
    房间 key = "collab:{workspaceId}:{productId}"
    """

    def can_decode(self, msg: WSMessage) -> bool:
        return msg.type in COLLAB_TYPES

    async def process(self, user_login: str, websocket: WebSocket, msg: WSMessage):
        msg_type = msg.type
        workspace_id = msg.get_string("workspaceId") or ""
        product_id = msg.get_string("productId") or ""

        if not workspace_id:
            await ws_sessions.send(websocket, {
                "type": "ERROR",
                "message": "缺少 workspaceId",
            })
            return

        room_key = f"collab:{workspace_id}:{product_id}"
        room = room_manager.get_or_create(room_key)

        if msg_type == "COLLAB_JOIN":
            room.add_session(user_login, websocket)
            users = list(room.get_users())
            # 广播加入
            for u in users:
                await ws_sessions.broadcast(u, {
                    "type": "COLLAB_JOIN", "user": user_login,
                    "workspaceId": workspace_id, "productId": product_id,
                })
            await ws_sessions.send(websocket, {
                "type": "COLLAB_USER_LIST",
                "users": users,
                "workspaceId": workspace_id, "productId": product_id,
            })

        elif msg_type == "COLLAB_LEAVE":
            room.remove_session(user_login, websocket)
            for u in room.get_users():
                await ws_sessions.broadcast(u, {
                    "type": "COLLAB_LEAVE", "user": user_login,
                    "workspaceId": workspace_id, "productId": product_id,
                })

        else:
            # 转发消息给同房间其他用户
            payload = msg.to_dict()
            payload["user"] = user_login
            for u in room.get_users():
                if u != user_login:
                    await ws_sessions.broadcast(u, payload)


collaborative_module = CollaborativeModule()
