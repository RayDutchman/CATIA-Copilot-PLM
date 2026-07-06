"""WorkspaceWorkflowKey 复合主键。"""
from dataclasses import dataclass
@dataclass(frozen=True)
class WorkspaceWorkflowKey:
    workspace_id: str; workflowmodel_id: str
