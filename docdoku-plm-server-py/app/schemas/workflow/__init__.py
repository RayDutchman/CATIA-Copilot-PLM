"""工作流相关 Pydantic DTO，字段名与 DocdokuPLM JSON 响应保持一致（camelCase）。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class TaskHolderDocDTO(BaseModel):
    """task 关联的文档简要信息"""
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    id: str
    version: str
    workspaceId: str
    documentMasterId: str
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    checkOutUser: Optional[dict] = None
    checkOutDate: Optional[int] = None
    path: Optional[str] = None
    author: Optional[dict] = None
    creationDate: Optional[int] = None



class TaskHolderPartDTO(BaseModel):
    """task 关联的零件简要信息"""
    model_config = ConfigDict(extra='forbid')
    partKey: str
    partNumber: Optional[str] = None
    version: str
    name: Optional[str] = None
    workspaceId: str
    description: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    checkOutUser: Optional[dict] = None
    checkOutDate: Optional[int] = None
    standardPart: bool = False
    author: Optional[dict] = None
    creationDate: Optional[int] = None


class TaskWrapperDTO(BaseModel):
    """assigned tasks 包装响应"""
    model_config = ConfigDict(extra='forbid')
    num: int
    title: Optional[str] = None
    instructions: Optional[str] = None
    status: Optional[str] = None
    worker: Optional[UserDTO] = None
    closureComment: Optional[str] = None
    signature: Optional[str] = None
    closureDate: Optional[str] = None
    holderType: Optional[str] = None   # "document" | "part" | "workspace-workflow"
    holderReference: Optional[str] = None
    holderVersion: Optional[str] = None
    workspaceId: Optional[str] = None

    # 附加字段（assigned tasks 列表中的扩展字段）
    workflowId: Optional[int] = None
    activityStep: Optional[int] = None
    targetIteration: Optional[int] = None
    assignedUsers: List[UserDTO] = []
    assignedGroups: List[dict] = []



class WorkflowAbortedDTO(BaseModel):
    """aborted workflow 实例列表响应"""
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    id: int
    abortedDate: Optional[str] = None
    finalLifecycleState: Optional[str] = None



class WorkspaceWorkflowMinimalDTO(BaseModel):
    """workspace-workflow 简要列表响应"""
    model_config = ConfigDict(extra='forbid')
    id: Optional[str] = None
    abortedDate: Optional[str] = None
    finalLifecycleState: Optional[str] = None



from app.schemas.part import UserDTO


class ACLDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    userEntries: Optional[dict[str, str]] = None  # "login:workspaceId" -> permission
    groupEntries: Optional[dict[str, str]] = None

# Re-exports from split files
from app.schemas.workflow.activity_model import ActivityModelDTO  # noqa: E402, F401
from app.schemas.workflow.workflow_model import WorkflowModelDTO  # noqa: E402, F401
from app.schemas.workflow.task import TaskDTO  # noqa: E402, F401
from app.schemas.workflow.activity import WorkflowActivityDTO  # noqa: E402, F401
from app.schemas.workflow.workflow import WorkflowDTO  # noqa: E402, F401
from app.schemas.workflow.task_model import TaskModelDTO  # noqa: E402, F401

# Forward-reference resolution
TaskDTO.model_rebuild()
WorkflowModelDTO.model_rebuild()
TaskWrapperDTO.model_rebuild()
