"""TaskKey 复合主键。"""
from dataclasses import dataclass
@dataclass(frozen=True)
class TaskKey:
    workflow_id: int; activity_step: int; num: int
