"""事件载体: DocumentRevisionEvent — 携带被操作的文档版本。"""
from __future__ import annotations
from typing import Optional
from dataclasses import dataclass


@dataclass
class DocumentRevisionEvent:
    observedDocument: Optional[object] = None
