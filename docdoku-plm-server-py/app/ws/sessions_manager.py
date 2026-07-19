"""WebSocket 会话管理器（对标 WebSocketSessionsManager — @ApplicationScoped 单例 + ConcurrentHashMap）。

维护 user_login → List[WebSocket] 映射，管理会话生命周期、广播发送。
"""
import asyncio
import logging
from typing import Optional
from fastapi import WebSocket

_logger = logging.getLogger(__name__)


class WSSessionsManager:
    """单例 WebSocket 会话管理器。"""

    def __init__(self):
        self._sessions: dict[str, list[WebSocket]] = {}

    def get_sessions(self, user_login: str) -> list[WebSocket]:
        return self._sessions.get(user_login, [])

    def has_sessions(self, user_login: str) -> bool:
        return bool(self.get_sessions(user_login))

    def add_session(self, user_login: str, ws: WebSocket):
        if user_login not in self._sessions:
            self._sessions[user_login] = []
        if ws not in self._sessions[user_login]:
            self._sessions[user_login].append(ws)
        _logger.debug("WS session added: %s (total=%d)", user_login,
                       len(self._sessions[user_login]))

    def remove_session(self, ws: WebSocket, user_login: str | None = None):
        """移除会话，若未提供 login 则自行查找。"""
        if user_login is None:
            user_login = self.get_owner(ws)
        if user_login and user_login in self._sessions:
            sessions = self._sessions[user_login]
            if ws in sessions:
                sessions.remove(ws)
            if not sessions:
                del self._sessions[user_login]
            _logger.debug("WS session removed: %s", user_login)

    def get_owner(self, ws: WebSocket) -> str | None:
        """查找 WebSocket 所属用户。"""
        for login, sessions in self._sessions.items():
            if ws in sessions:
                return login
        return None

    async def send(self, ws: WebSocket, data: dict | str):
        """向单个 WebSocket 发送消息。"""
        try:
            if isinstance(data, str):
                await ws.send_text(data)
            else:
                from app.ws.message import WSMessage
                await ws.send_text(WSMessage(data).to_json())
        except Exception:
            _logger.warning("WS send 失败")

    async def broadcast(self, user_login: str, data: dict):
        """向某用户的所有 WebSocket 连接广播消息。"""
        tasks = [self.send(ws, data) for ws in self.get_sessions(user_login)]
        if tasks:
            await asyncio.gather(*tasks)

    def is_allowed_to_reach_user(self, sender: str, remote_user: str) -> bool:
        """检查两个用户是否共享至少一个工作区（对齐 Java UserManagerBean.hasCommonWorkspace）。"""
        import threading
        # WebSocket 模块不在 FastAPI 请求上下文中，需手动创建 DB session
        try:
            from app.core.database import SessionLocal
            db = SessionLocal()
            try:
                row = db.execute(
                    __import__('sqlalchemy').text(
                        "SELECT 1 FROM userdata u1 "
                        "JOIN userdata u2 ON u1.workspace_id = u2.workspace_id "
                        "WHERE u1.login = :s AND u2.login = :r LIMIT 1"
                    ), {"s": sender, "r": remote_user}
                ).first()
                return row is not None
            finally:
                db.close()
        except Exception:
            _logger.exception("is_allowed_to_reach_user 查询失败")
            return False


ws_sessions = WSSessionsManager()
