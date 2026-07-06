"""ConfigurationItemKey 复合主键。"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ConfigurationItemKey:
    workspace_id: str
    id: str
