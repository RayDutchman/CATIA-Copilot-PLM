"""DTO: BaselinedDocumentOptionDTO."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict


class BaselinedDocumentOptionDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    version: str = ""
    lastIteration: int = 0
    released: bool = False
    obsolete: bool = False
