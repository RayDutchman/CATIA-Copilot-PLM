"""DTO: PlatformOptionsDTO."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict


class PlatformOptionsDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    registrationStrategy: Optional[str] = None
    workspaceCreationStrategy: Optional[str] = None
