"""DTO: CountDTO."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict


class CountDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    count: int = 0
