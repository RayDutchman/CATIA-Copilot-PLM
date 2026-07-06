"""DTO: LightPartRevisionDTO."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional


class LightPartRevisionDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    workspaceId: Optional[str] = None
    partNumber: Optional[str] = None
    version: Optional[str] = None
