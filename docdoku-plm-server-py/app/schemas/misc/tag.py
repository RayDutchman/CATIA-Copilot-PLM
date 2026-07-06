"""DTO: TagDTO. Auto-split from misc.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class TagDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    id: str
    label: Optional[str] = None
    workspaceId: Optional[str] = None


# ============ LOV (List of Values) ============
