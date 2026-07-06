"""DTO: TaskProcessDTO."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict


class TaskProcessDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    action: Optional[str] = None
    comment: Optional[str] = None
    signature: Optional[str] = None
