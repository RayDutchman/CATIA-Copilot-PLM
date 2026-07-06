"""DocumentMasterTemplateKey 复合主键。"""
from dataclasses import dataclass
@dataclass(frozen=True)
class DocumentMasterTemplateKey:
    workspace_id: str; id: str
