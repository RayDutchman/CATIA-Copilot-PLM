"""DTO: BaselinedDocumentDTO. Auto-split from document.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class BaselinedDocumentDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    documentMasterId: Optional[str] = None
    version: Optional[str] = None
    iteration: Optional[int] = None
