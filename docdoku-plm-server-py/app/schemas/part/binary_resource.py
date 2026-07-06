"""DTO: BinaryResourceDTO. Auto-split from part.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List


class BinaryResourceDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')
    fullName: str
    name: Optional[str] = None
    contentLength: Optional[int] = None
    lastModified: Optional[datetime] = None
