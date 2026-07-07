"""WebRTC 信令 WebSocket 模块（对标 WebRTCWebSocketModule + Impl）。

消息类型: WEBRTC_OFFER / ANSWER / ICE_CANDIDATE / HANGUP / CALL / REJECT
用于 P2P 视频通话的 SDP/ICE 候选信令中继。
"""
import logging
from fastapi import WebSocket
from app.ws.module import WebSocketModule
from app.ws.message import WSMessage
from app.ws.sessions_manager import ws_sessions
from app.ws.room import room_manager
from app.ws.webrtc_utils import (
    WEBRTC_OFFER, WEBRTC_ANSWER, WEBRTC_ICE_CANDIDATE,
    WEBRTC_HANGUP, WEBRTC_CALL, WEBRTC_REJECT,
    create_hangup_message,
)

_logger = logging.getLogger(__name__)

WEBRTC_TYPES = {
    WEBRTC_OFFER, WEBRTC_ANSWER, WEBRTC_ICE_CANDIDATE,
    WEBRTC_HANGUP, WEBRTC_CALL, WEBRTC_REJECT,
}


class WebRTCModule(WebSocketModule):
    """WebRTC 信令中继模块。

    房间 key = "webrtc:{roomKey}" — 1:1 通话场景。
    消息转发逻辑: sender → room 中的另一个用户。
    """

    def can_decode(self, msg: WSMessage) -> bool:
        return msg.type in WEBRTC_TYPES

    async def process(self, user_login: str, websocket: WebSocket, msg: WSMessage):
        msg_type = msg.type
        remote_user = msg.get_string("remoteUser")
        room_key = msg.get_string("roomKey") or ""
        rtc_room_key = f"webrtc:{room_key}"

        if msg_type == WEBRTC_HANGUP:
            # 挂断 → 通知同房间另一用户
            if remote_user:
                hangup_msg = create_hangup_message(user_login, rtc_room_key)
                await ws_sessions.broadcast(remote_user, hangup_msg)
            # 清理通话房间
            room = room_manager.get(rtc_room_key)
            if room:
                room.remove_session(user_login, websocket)
                room_manager.remove_if_empty(rtc_room_key)

        elif remote_user:
            # 直转给 remoteUser（offer/answer/ice/call/reject）
            if not ws_sessions.has_sessions(remote_user):
                await ws_sessions.send(websocket, {
                    "type": WEBRTC_REJECT,
                    "sender": remote_user,
                    "roomKey": rtc_room_key,
                    "reason": "用户不在线",
                })
                return

            # 加入房间
            room = room_manager.get_or_create(rtc_room_key)
            room.add_session(user_login, websocket)

            # 转发
            relay = msg.to_dict()
            relay["sender"] = user_login
            await ws_sessions.broadcast(remote_user, relay)
        else:
            _logger.warning("WebRTC 消息缺少 remoteUser: type=%s", msg_type)


webrtc_module = WebRTCModule()
