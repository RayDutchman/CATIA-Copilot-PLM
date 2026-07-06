"""DTO: WorkspaceFrontOptionsDTO."""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class WorkspaceFrontOptionsDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    partTableColumns: Optional[List[str]] = None
    documentTableColumns: Optional[List[str]] = None
