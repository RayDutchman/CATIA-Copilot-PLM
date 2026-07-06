"""DTO: LayerDTO. Auto-split from product.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class LayerDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: Optional[int] = None
    name: Optional[str] = None
    color: Optional[str] = None
    workspaceId: Optional[str] = None
    configurationItemId: Optional[str] = None
