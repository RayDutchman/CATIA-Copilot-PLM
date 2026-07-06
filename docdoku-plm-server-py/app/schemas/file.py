"""DTO: FileDTO."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict


class FileDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    created: bool = False
    fullName: str = ""
    shortName: str = ""
