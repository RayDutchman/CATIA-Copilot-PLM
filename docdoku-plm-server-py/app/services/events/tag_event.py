"""事件载体: TagEvent — 携带被操作的标签及关联文档/零件。"""
from __future__ import annotations
from typing import Optional
from dataclasses import dataclass


@dataclass
class TagEvent:
    observedTag: Optional[object] = None
    taggableDocument: Optional[object] = None
    taggablePart: Optional[object] = None
