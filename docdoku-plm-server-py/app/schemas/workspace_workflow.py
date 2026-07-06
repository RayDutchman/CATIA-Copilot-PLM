"""DTO: WorkspaceWorkflowDTO."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict


class WorkspaceWorkflowDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    workspaceId: Optional[str] = None
    id: Optional[str] = None
    workflow: Optional[dict] = None
