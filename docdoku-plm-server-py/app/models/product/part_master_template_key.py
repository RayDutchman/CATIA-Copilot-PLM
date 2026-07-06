"""PartMasterTemplateKey 复合主键。"""
from dataclasses import dataclass


@dataclass(frozen=True)
class PartMasterTemplateKey:
    workspace_id: str
    id: str
