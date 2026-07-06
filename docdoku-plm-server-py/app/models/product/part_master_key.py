"""PartMasterKey 复合主键。"""
from dataclasses import dataclass


@dataclass(frozen=True)
class PartMasterKey:
    workspace_id: str
    number: str
