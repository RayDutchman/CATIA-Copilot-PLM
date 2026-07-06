"""PathChoice DTO。"""
from dataclasses import dataclass, field
from typing import List

@dataclass
class PathChoice:
    resolved_path: List[int] = field(default_factory=list)
