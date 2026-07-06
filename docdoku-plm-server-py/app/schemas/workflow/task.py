"""DTO: TaskDTO. Auto-split from workflow.py."""
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class TaskDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

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
