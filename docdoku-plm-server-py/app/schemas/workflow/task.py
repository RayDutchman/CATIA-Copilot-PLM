"""DTO: TaskDTO. Auto-split from workflow.py."""
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.schemas.part.user import UserDTO
from app.schemas.user_mgmt.user_group import UserGroupDTO


class TaskDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    num: int
    title: Optional[str] = None
    instructions: Optional[str] = None
    status: Optional[str] = None  # NOT_STARTED / IN_PROGRESS / APPROVED / REJECTED
    worker: Optional[UserDTO] = None
    assignedUsers: List[UserDTO] = []
    assignedGroups: List[UserGroupDTO] = []
    targetIteration: Optional[int] = None
    closureDate: Optional[str] = None
    closureComment: Optional[str] = None
    signature: Optional[str] = None
    duration: Optional[int] = None
