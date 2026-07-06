"""DTO: PlatformHealthDTO."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict


class PlatformHealthDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    status: Optional[str] = None
    executionTime: int = 0
