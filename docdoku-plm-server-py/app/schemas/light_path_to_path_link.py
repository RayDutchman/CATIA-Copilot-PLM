"""DTO: LightPathToPathLinkDTO."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict


class LightPathToPathLinkDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: Optional[int] = None
    type: Optional[str] = None
    sourcePath: Optional[str] = None
    targetPath: Optional[str] = None
    description: Optional[str] = None
