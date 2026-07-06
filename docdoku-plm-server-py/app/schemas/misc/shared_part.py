"""DTO: SharedPartDTO. Auto-split from misc.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from app.schemas.part import UserDTO


class SharedPartDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    partNumber: Optional[str] = None
    version: Optional[str] = None
    workspaceId: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    author: Optional[UserDTO] = None
    creationDate: Optional[str] = None


# ============ Effectivity ============
