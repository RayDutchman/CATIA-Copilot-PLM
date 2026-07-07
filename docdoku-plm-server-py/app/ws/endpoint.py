"""WebSocket 端点（对标 WebSocketApplication + Decoder/Encoder）。

FastAPI 原生 WebSocket，路径 /ws。
认证流程：首条消息 type=AUTH，携带 JWT token。
"""
import json
import logging
from fastapi import WebSocket, WebSocketDisconnect
from app.ws.message import WSMessage
from app.ws.sessions_manager import ws_sessions

_logger = logging.getLogger(__name__)


async def handle_websocket(websocket: WebSocket):
    """WebSocket 主连接处理循环。

    客户端连上后先发 AUTH 消息，认证成功后才处理后续业务消息。
    """
    await websocket.accept()
    authenticated = False
    user_login: str | None = None

    try:
        while True:
            raw = await websocket.receive_text()
            msg = WSMessage(raw)

            if not authenticated:
                user_login = await _authenticate(websocket, msg)
                if user_login:
                    authenticated = True
                    ws_sessions.add_session(user_login, websocket)
                    await websocket.send_text(
                        WSMessage({"type": "AUTH_OK", "login": user_login}).to_json()
                    )
                else:
                    await websocket.close(code=4001, reason="Auth failed")
                    return
                continue

            # 路由到模块处理
            await _dispatch(user_login, websocket, msg)

    except WebSocketDisconnect:
        pass
    except Exception:
        _logger.exception("WebSocket error for user=%s", user_login)
    finally:
        if user_login:
            ws_sessions.remove_session(websocket, user_login)


async def _authenticate(websocket: WebSocket, msg: WSMessage) -> str | None:
    """验证首条 AUTH 消息。"""
    if msg.type != "AUTH":
        return None
    jwt = msg.get_string("jwt")
    if not jwt:
        return None
    try:
        from app.core.security import verify_token
        payload = verify_token(jwt)
        return payload.get("login")
    except Exception:
        _logger.warning("WebSocket JWT 验证失败")
        return None


async def _dispatch(user_login: str, websocket: WebSocket, msg: WSMessage):
    """将消息路由到匹配的 WebSocketModule。"""
    from app.ws.chat_module import chat_module
    from app.ws.collaborative_module import collaborative_module
    from app.ws.status_module import status_module
    from app.ws.webrtc_module import webrtc_module

    for mod in [chat_module, collaborative_module, status_module, webrtc_module]:
        if mod.can_decode(msg):
            await mod.process(user_login, websocket, msg)
            return

    _logger.warning("无模块处理消息 type=%s", msg.type)
