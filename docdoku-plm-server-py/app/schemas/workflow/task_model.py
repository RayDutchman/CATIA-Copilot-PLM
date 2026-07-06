"""DTO: TaskModelDTO. Auto-split from workflow.py."""
from typing import Optional
from pydantic import BaseModel, ConfigDict


class TaskModelDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    num: int
    title: Optional[str] = None
    instructions: Optional[str] = None
    duration: Optional[int] = None
    role: Optional[dict] = None  # RoleDTO (name, workspaceId)
