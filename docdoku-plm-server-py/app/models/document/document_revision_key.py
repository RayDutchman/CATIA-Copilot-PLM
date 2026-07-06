"""DocumentRevisionKey 复合主键。"""
from dataclasses import dataclass
@dataclass(frozen=True)
class DocumentRevisionKey:
    workspace_id: str; documentmaster_id: str; version: str
