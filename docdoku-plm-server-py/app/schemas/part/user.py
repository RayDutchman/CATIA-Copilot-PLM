"""DTO: UserDTO. Auto-split from part.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class UserDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')
    login: str
    name: Optional[str] = None
    email: Optional[str] = None
    language: Optional[str] = None
    workspaceId: Optional[str] = None
    membership: Optional[dict] = None
