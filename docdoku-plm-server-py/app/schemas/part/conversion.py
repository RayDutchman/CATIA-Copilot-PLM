"""DTO: ConversionDTO. Auto-split from part.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List


class ConversionDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    pending: bool = False
    succeed: bool = False
    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None
