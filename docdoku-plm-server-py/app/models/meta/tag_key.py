"""TagKey 复合主键。"""
from dataclasses import dataclass
@dataclass(frozen=True)
class TagKey:
    workspace_id: str; label: str
