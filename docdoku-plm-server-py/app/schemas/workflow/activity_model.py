"""DTO: ActivityModelDTO. Auto-split from workflow.py."""
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class ActivityModelDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    step: int
    type: Optional[str] = None
    lifeCycleState: Optional[str] = None
    tasksToComplete: Optional[int] = None
    taskModels: List[TaskModelDTO] = []
