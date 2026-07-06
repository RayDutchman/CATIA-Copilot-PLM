"""CDI Qualifier: 事件标记 — 去标签。"""
from dataclasses import dataclass


@dataclass
class Untagged:
    """标记去标签操作的事件限定符。"""
    pass
