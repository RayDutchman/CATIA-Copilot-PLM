"""OperationSecurityStrategy DTO。"""
from dataclasses import dataclass, field
from typing import List
@dataclass
class OperationSecurityStrategy:
    enabled: bool = False
    operations: List[str] = field(default_factory=list)
