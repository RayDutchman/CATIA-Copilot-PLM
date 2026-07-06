"""DTO: WorkflowActivityDTO. Auto-split from workflow.py."""
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class WorkflowActivityDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

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
