"""CascadeResult DTO。"""
from dataclasses import dataclass, field
from typing import List

@dataclass
class CascadeResult:
    part_links: List[dict] = field(default_factory=list)
    document_links: List[dict] = field(default_factory=list)
