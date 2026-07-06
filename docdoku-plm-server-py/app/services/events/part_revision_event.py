"""事件载体: PartRevisionEvent — 携带被操作的零件版本。"""
from __future__ import annotations
from typing import Optional
from dataclasses import dataclass


@dataclass
class PartRevisionEvent:
    observedPart: Optional[object] = None
