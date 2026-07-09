"""DTO: OrganizationDTO. Auto-split from misc.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class OrganizationDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str
    description: Optional[str] = None
    owner: Optional[str] = None
