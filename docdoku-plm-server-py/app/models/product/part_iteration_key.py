"""PartIterationKey 复合主键。"""
from dataclasses import dataclass


@dataclass(frozen=True)
class PartIterationKey:
    workspace_id: str
    partmaster_partnumber: str
    partrevision_version: str
    iteration: int
