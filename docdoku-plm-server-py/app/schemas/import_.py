"""DTO: ImportDTO."""
from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class ImportDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: Optional[str] = None
    fileName: Optional[str] = None
    endDate: Optional[datetime] = None
    startDate: Optional[datetime] = None
    succeed: bool = False
    pending: bool = False
    errors: List[str] = []
    warnings: List[str] = []
