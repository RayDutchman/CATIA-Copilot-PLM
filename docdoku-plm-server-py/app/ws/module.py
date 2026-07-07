"""WebSocket 模块抽象基类（对标 WebSocketModule 接口）。"""
from abc import ABC, abstractmethod
from fastapi import WebSocket
from app.ws.message import WSMessage


class WebSocketModule(ABC):
    """可插拔 WebSocket 消息处理模块。

    子类需实现 can_decode（类型匹配）和 process（业务处理）。
    """

    @abstractmethod
    def can_decode(self, msg: WSMessage) -> bool:
        """判断是否可处理该消息类型。"""
        ...

    @abstractmethod
    async def process(self, user_login: str, websocket: WebSocket, msg: WSMessage):
        """处理消息。"""
        ...
