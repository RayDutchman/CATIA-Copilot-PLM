"""DTO: MarkerDTO. Auto-split from product.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class MarkerDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: Optional[int] = None
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    title: Optional[str] = None
    description: Optional[str] = None
    layerId: Optional[int] = None
