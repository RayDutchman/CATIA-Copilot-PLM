"""TaskModelKey 复合主键。"""
from dataclasses import dataclass
@dataclass(frozen=True)
class TaskModelKey:
    activitymodel_id: int; num: int
