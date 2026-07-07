"""房间管理（对标 Room.java + RoomSession）。

房间由 context（如 workspace_id + 实体 key）标识。
每个房间维护 user_login → WebSocket 映射，支持多用户。
"""
import logging
from dataclasses import dataclass, field
from fastapi import WebSocket

_logger = logging.getLogger(__name__)


class Room:
    """WebSocket 房间（多用户消息组）。"""

    def __init__(self, key: str):
        self._key = key
        self._users: dict[str, list[WebSocket]] = {}

    @property
    def key(self) -> str:
        return self._key

    def add_session(self, user_login: str, ws: WebSocket):
        if user_login not in self._users:
            self._users[user_login] = []
        if ws not in self._users[user_login]:
            self._users[user_login].append(ws)
        _logger.debug("Room %s: user %s joined (total=%d)", self._key, user_login,
                       len(self._users))

    def remove_session(self, user_login: str, ws: WebSocket):
        if user_login in self._users:
            sessions = self._users[user_login]
            if ws in sessions:
                sessions.remove(ws)
            if not sessions:
                del self._users[user_login]
        _logger.debug("Room %s: user %s left", self._key, user_login)

    def get_users(self) -> set[str]:
        return set(self._users.keys())

    def get_other_user_sessions(self, ws: WebSocket) -> list[WebSocket]:
        """获取房间内除指定 WS 外的所有会话。"""
        result = []
        for login, sessions in self._users.items():
            for s in sessions:
                if s is not ws:
                    result.append(s)
        return result

    def get_other_user_ws(self, myself: str) -> WebSocket | None:
        """获取房间中另一个人的 WebSocket（用于 1:1 场景）。"""
        for login, sessions in self._users.items():
            if login != myself and sessions:
                return sessions[0]
        return None

    @property
    def is_empty(self) -> bool:
        return not self._users

    def __repr__(self):
        return f"Room(key={self._key!r}, users={list(self._users.keys())})"


class RoomManager:
    """房间管理器（全局单例）。"""

    def __init__(self):
        self._rooms: dict[str, Room] = {}

    def get_or_create(self, key: str) -> Room:
        if key not in self._rooms:
            self._rooms[key] = Room(key)
        return self._rooms[key]

    def get(self, key: str) -> Room | None:
        return self._rooms.get(key)

    def remove_if_empty(self, key: str):
        room = self._rooms.get(key)
        if room and room.is_empty:
            del self._rooms[key]

    def get_user_rooms(self, user_login: str) -> list[Room]:
        return [r for r in self._rooms.values() if user_login in r.get_users()]


room_manager = RoomManager()
