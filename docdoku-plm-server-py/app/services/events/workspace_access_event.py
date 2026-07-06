"""事件载体: WorkspaceAccessEvent — 携带当前连接的用户。"""
from __future__ import annotations
from typing import Optional
from dataclasses import dataclass


@dataclass
class WorkspaceAccessEvent:
    connectedUser: Optional[object] = None
