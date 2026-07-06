"""DTO: RoleMappingDTO."""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class RoleMappingDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    roleName: Optional[str] = None
    userLogins: List[str] = []
    groupIds: List[str] = []
