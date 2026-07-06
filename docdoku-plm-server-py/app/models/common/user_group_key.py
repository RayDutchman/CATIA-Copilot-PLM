"""UserGroupKey 复合主键 — 对应 Java @IdClass。"""
from dataclasses import dataclass


@dataclass(frozen=True)
class UserGroupKey:
    workspace_id: str
    id: str
