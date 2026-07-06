"""DTO: WorkspaceBackOptionsDTO."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict


class WorkspaceBackOptionsDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    workspaceId: Optional[str] = None
    sendEmails: bool = False
