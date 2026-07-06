"""事件载体: WorkspaceEvent — 携带被操作的工作区。"""
from __future__ import annotations
from typing import Optional
from dataclasses import dataclass


@dataclass
class WorkspaceEvent:
    observedWorkspace: Optional[object] = None
