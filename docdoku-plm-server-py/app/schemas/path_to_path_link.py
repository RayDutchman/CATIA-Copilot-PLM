"""DTO: PathToPathLinkDTO."""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class PathToPathLinkDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: Optional[int] = None
    type: Optional[str] = None
    description: Optional[str] = None
    sourceComponents: List[dict] = []
    targetComponents: List[dict] = []
