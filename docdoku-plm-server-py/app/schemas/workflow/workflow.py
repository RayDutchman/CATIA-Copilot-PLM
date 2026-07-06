"""DTO: WorkflowDTO. Auto-split from workflow.py."""
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class WorkflowDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    id: int
    abortedDate: Optional[str] = None
    finalLifecycleState: Optional[str] = None
    activities: List[WorkflowActivityDTO] = []
    currentStep: int = 0
