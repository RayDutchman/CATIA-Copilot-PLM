"""DTO: WorkspaceListDTO."""
from __future__ import annotations
from typing import List
from pydantic import BaseModel, ConfigDict


class WorkspaceListDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    administratedWorkspaces: List[dict] = []
    allWorkspaces: List[dict] = []
