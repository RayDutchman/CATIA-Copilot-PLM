"""DTO: UserGroupDTO. Auto-split from user_mgmt.py."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict


class UserGroupDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    id: str
    workspaceId: Optional[str] = None
