"""事件载体: PartIterationEvent — 携带被操作的零件迭代。"""
from __future__ import annotations
from typing import Optional
from dataclasses import dataclass


@dataclass
class PartIterationEvent:
    observedPart: Optional[object] = None
