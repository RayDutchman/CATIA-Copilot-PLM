"""UserKey 复合主键 — 对应 Java @IdClass。"""
from dataclasses import dataclass


@dataclass(frozen=True)
class UserKey:
    workspace_id: str
    login: str
