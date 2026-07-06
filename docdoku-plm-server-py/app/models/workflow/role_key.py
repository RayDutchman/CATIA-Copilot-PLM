"""RoleKey 复合主键。"""
from dataclasses import dataclass
@dataclass(frozen=True)
class RoleKey:
    workspace_id: str; name: str
