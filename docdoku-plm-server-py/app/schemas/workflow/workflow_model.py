"""DTO: WorkflowModelDTO. Auto-split from workflow.py."""
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.schemas.part.user import UserDTO


class WorkflowModelDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    id: str
    workspaceId: Optional[str] = None
    finalLifeCycleState: Optional[str] = None
    creationDate: Optional[str] = None
    author: Optional[UserDTO] = None
    acl: Optional["ACLDTO"] = None
    activityModels: List["ActivityModelDTO"] = []
