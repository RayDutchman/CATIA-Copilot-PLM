"""DTO: ResolvedPartLinkDTO."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ResolvedPartLinkDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    partIteration: Optional[dict] = None
    partLink: Optional[dict] = None
