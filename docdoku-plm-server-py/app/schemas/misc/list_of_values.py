"""DTO: LOVDTO. Auto-split from misc.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class LOVDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str
    id: Optional[str] = None
    workspaceId: Optional[str] = None
    values: List[LOVValueDTO] = []
    deletable: Optional[bool] = None


# ============ Attribute ============
