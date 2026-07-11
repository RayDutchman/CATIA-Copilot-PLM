"""DTO: DocumentBaselineDTO. Auto-split from document.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from app.schemas.part import UserDTO


class DocumentBaselineDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    creationDate: Optional[str] = None
    author: Optional[UserDTO] = None
    baselinedDocuments: List[BaselinedDocumentDTO] = []
