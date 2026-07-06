"""DTO: AttributeDTO. Auto-split from misc.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class AttributeDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    type: Optional[str] = None
    name: Optional[str] = None
    value: Optional[str] = None
    mandatory: Optional[bool] = None


# ============ Health ============
