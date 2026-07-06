"""DTO: RoleDTO. Auto-split from misc.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class RoleDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    id: Optional[str] = None
    name: str
    workspaceId: Optional[str] = None
    defaultAssignedUsers: List[dict] = []
    defaultAssignedGroups: List[dict] = []


# ============ Tag ============
