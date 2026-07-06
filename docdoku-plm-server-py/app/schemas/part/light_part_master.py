"""DTO: LightPartMasterDTO. Auto-split from part.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class LightPartMasterDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')
    partNumber: str
    partName: str = ""
