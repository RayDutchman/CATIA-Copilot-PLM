"""事件载体: UserEvent — 携带被操作的用户。"""
from __future__ import annotations
from typing import Optional
from dataclasses import dataclass


@dataclass
class UserEvent:
    observedUser: Optional[object] = None
