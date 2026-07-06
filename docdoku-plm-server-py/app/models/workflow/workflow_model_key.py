"""WorkflowModelKey 复合主键。"""
from dataclasses import dataclass
@dataclass(frozen=True)
class WorkflowModelKey:
    workspace_id: str; id: str
