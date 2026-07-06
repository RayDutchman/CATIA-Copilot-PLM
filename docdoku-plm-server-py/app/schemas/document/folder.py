"""DTO: FolderDTO. Auto-split from document.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class FolderDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: Optional[str] = None
    name: Optional[str] = None
    path: Optional[str] = None
    home: Optional[bool] = None
