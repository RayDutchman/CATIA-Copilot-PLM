"""DTO: TagSubscriptionDTO."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict


class TagSubscriptionDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    tag: str = ""
    onIterationChange: bool = False
    onStateChange: bool = False
