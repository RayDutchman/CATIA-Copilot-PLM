"""DTO: TagListDTO."""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class TagListDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    tags: List["TagDTO"] = []


from app.schemas.misc.tag import TagDTO  # noqa: E402

TagListDTO.model_rebuild()
