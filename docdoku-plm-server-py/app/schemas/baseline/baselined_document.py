"""DTO: BaselinedDocumentDTO."""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class BaselinedDocumentDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    documentMasterId: Optional[str] = None
    title: Optional[str] = None
    version: Optional[str] = None
    iteration: Optional[int] = None
    availableIterations: List["BaselinedDocumentOptionDTO"] = []


from app.schemas.baseline.baselined_document_option import BaselinedDocumentOptionDTO  # noqa: E402

BaselinedDocumentDTO.model_rebuild()
