"""DTO: PathDTO."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict


class PathDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    path: Optional[str] = None
