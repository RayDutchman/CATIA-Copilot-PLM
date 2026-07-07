"""WebRTC 信令工具（对标 WebSocketUtils — 构造 WebRTC 消息 + 会话 Description 查询）。"""
from app.ws.message import create_message

# WebRTC 消息类型常量
WEBRTC_OFFER = "WEBRTC_OFFER"
WEBRTC_ANSWER = "WEBRTC_ANSWER"
WEBRTC_ICE_CANDIDATE = "WEBRTC_ICE_CANDIDATE"
WEBRTC_HANGUP = "WEBRTC_HANGUP"
WEBRTC_CALL = "WEBRTC_CALL"
WEBRTC_REJECT = "WEBRTC_REJECT"


def create_webrtc_message(
    msg_type: str,
    sender: str,
    room_key: str,
    sdp: str | None = None,
    remote_user: str | None = None,
    label: int | None = None,
    candidate_id: str | None = None,
    candidate_sdp_mline_index: int | None = None,
    candidate: str | None = None,
) -> dict:
    """构建标准 WebRTC 信令消息 dict。"""
    msg: dict = {
        "type": msg_type,
        "sender": sender,
        "roomKey": room_key,
    }
    if sdp is not None:
        msg["sdp"] = sdp
    if remote_user is not None:
        msg["remoteUser"] = remote_user
    if label is not None:
        msg["label"] = label
    if candidate_id is not None:
        msg["id"] = candidate_id
    if candidate_sdp_mline_index is not None:
        msg["sdpMLineIndex"] = candidate_sdp_mline_index
    if candidate is not None:
        msg["candidate"] = candidate
    return msg


def create_hangup_message(sender: str, room_key: str) -> dict:
    return create_webrtc_message(WEBRTC_HANGUP, sender, room_key)
