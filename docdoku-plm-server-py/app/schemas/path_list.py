"""DTO: PathListDTO."""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class PathListDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    configSpec: Optional[str] = None
    paths: List[str] = []
