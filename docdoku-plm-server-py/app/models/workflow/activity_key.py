"""ActivityKey 复合主键。"""
from dataclasses import dataclass
@dataclass(frozen=True)
class ActivityKey:
    workflow_id: int; step: int
