"""DTO: BaselinedPartDTO."""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class BaselinedPartDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    number: Optional[str] = None
    name: Optional[str] = None
    version: Optional[str] = None
    iteration: Optional[int] = None
    availableIterations: List["BaselinedPartOptionDTO"] = []


from app.schemas.baseline.baselined_part_option import BaselinedPartOptionDTO  # noqa: E402

BaselinedPartDTO.model_rebuild()
