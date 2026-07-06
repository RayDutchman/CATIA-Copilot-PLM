"""DocumentIterationKey 复合主键。"""
from dataclasses import dataclass

@dataclass(frozen=True)
class DocumentIterationKey:
    workspace_id: str; documentmaster_id: str; documentrevision_version: str; iteration: int
