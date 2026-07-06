"""PartRevisionKey 复合主键。"""
from dataclasses import dataclass


@dataclass(frozen=True)
class PartRevisionKey:
    workspace_id: str
    partmaster_partnumber: str
    version: str
