"""DTO: WorkspaceDTO. Auto-split from admin.py."""
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class WorkspaceDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    id: str
    description: Optional[str] = None
    enabled: Optional[bool] = True
    folderLocked: Optional[bool] = False
