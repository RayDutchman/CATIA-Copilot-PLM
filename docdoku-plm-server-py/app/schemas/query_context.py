"""DTO: QueryContextDTO."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict


class QueryContextDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    workspaceId: Optional[str] = None
    serialNumber: Optional[str] = None
    configurationItemId: Optional[str] = None
