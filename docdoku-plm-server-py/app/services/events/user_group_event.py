"""事件载体: UserGroupEvent — 携带被操作的用户组。"""
from __future__ import annotations
from typing import Optional
from dataclasses import dataclass


@dataclass
class UserGroupEvent:
    observedUserGroup: Optional[object] = None
