"""DTO: DocumentBaselineDTO."""
from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class DocumentBaselineDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    creationDate: Optional[datetime] = None
    type: Optional[str] = None
    baselinedDocuments: List["BaselinedDocumentDTO"] = []
    author: Optional[dict] = None


from app.schemas.baseline.baselined_document import BaselinedDocumentDTO  # noqa: E402

DocumentBaselineDTO.model_rebuild()
