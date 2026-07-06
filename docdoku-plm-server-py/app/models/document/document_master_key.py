"""DocumentMasterKey 复合主键。"""
from dataclasses import dataclass
@dataclass(frozen=True)
class DocumentMasterKey:
    workspace_id: str; id: str
