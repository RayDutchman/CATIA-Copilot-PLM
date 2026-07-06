"""工作流相关 Pydantic DTO，字段名与 DocdokuPLM JSON 响应保持一致（camelCase）。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

from app.schemas.part import UserDTO


class ACLDTO(BaseModel):
    userEntries: Optional[dict[str, str]] = None  # "login:workspaceId" -> permission
    groupEntries: Optional[dict[str, str]] = None


class TaskModelDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    num: int
    title: Optional[str] = None
    instructions: Optional[str] = None
    duration: Optional[int] = None
    role: Optional[dict] = None  # RoleDTO (name, workspaceId)


class ActivityModelDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    step: int
    type: Optional[str] = None
    lifeCycleState: Optional[str] = None
    tasksToComplete: Optional[int] = None
    taskModels: List[TaskModelDTO] = []


class WorkflowModelDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspaceId: Optional[str] = None
    finalLifeCycleState: Optional[str] = None
    creationDate: Optional[str] = None
    author: Optional[UserDTO] = None
    acl: Optional[ACLDTO] = None
    activityModels: List[ActivityModelDTO] = []


class TaskDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    num: int
    title: Optional[str] = None
    instructions: Optional[str] = None
    status: Optional[str] = None  # NOT_STARTED / IN_PROGRESS / APPROVED / REJECTED
    worker: Optional[UserDTO] = None
    assignedUsers: List[UserDTO] = []
    assignedGroups: List[dict] = []
    targetIteration: Optional[int] = None
    closureDate: Optional[str] = None
    closureComment: Optional[str] = None
    signature: Optional[str] = None
    duration: Optional[int] = None


class WorkflowActivityDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    step: int
    lifeCycleState: Optional[str] = None
    type: Optional[str] = None
    tasksToComplete: Optional[int] = None
    complete: int = 0
    stopped: bool = False
    inProgress: bool = False
    toDo: bool = False
    relaunchStep: Optional[int] = None
    tasks: List[TaskDTO] = []


class WorkflowDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    abortedDate: Optional[str] = None
    finalLifecycleState: Optional[str] = None
    activities: List[WorkflowActivityDTO] = []
    currentStep: int = 0


class WorkflowAbortedDTO(BaseModel):
    """aborted workflow 实例列表响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    abortedDate: Optional[str] = None
    finalLifecycleState: Optional[str] = None


class WorkspaceWorkflowMinimalDTO(BaseModel):
    """workspace-workflow 简要列表响应"""
    id: Optional[str] = None
    abortedDate: Optional[str] = None
    finalLifecycleState: Optional[str] = None


class TaskWrapperDTO(BaseModel):
    """assigned tasks 包装响应"""
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


class TaskHolderDocDTO(BaseModel):
    """task 关联的文档简要信息"""
    model_config = ConfigDict(from_attributes=True)

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
