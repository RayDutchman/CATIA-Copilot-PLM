"""WebSocket 消息容器（对标 WebSocketMessage — JSON + type 判别字段）。"""
import json
from typing import Any


class WSMessage:
    """WebSocket 消息（包装 JSON dict，type 字段做路由）。"""
    __slots__ = ("_data",)

    DISCRIMINATOR = "type"

    def __init__(self, data: dict | str):
        if isinstance(data, str):
            self._data = json.loads(data)
        else:
            self._data = data

    @property
    def type(self) -> str:
        return self._data.get(self.DISCRIMINATOR, "")

    def get(self, key: str, default=None) -> Any:
        return self._data.get(key, default)

    def get_string(self, key: str) -> str | None:
        v = self._data.get(key)
        return str(v) if v is not None else None

    def get_json(self, key: str) -> dict | None:
        v = self._data.get(key)
        return v if isinstance(v, dict) else None

    def get_int(self, key: str) -> int | None:
        try:
            return int(self._data.get(key, 0))
        except (TypeError, ValueError):
            return None

    def to_dict(self) -> dict:
        return dict(self._data)

    def to_json(self) -> str:
        return json.dumps(self._data, ensure_ascii=False)

    def __repr__(self):
        return f"WSMessage(type={self.type!r})"


def create_message(msg_type: str, **kwargs) -> WSMessage:
    """工厂函数，创建带 type 字段的消息。"""
    return WSMessage({WSMessage.DISCRIMINATOR: msg_type, **kwargs})
