"""DTO: PartUsageLinkDTO. Auto-split from part.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class PartUsageLinkDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: int = 0
    fullId: Optional[str] = None
    amount: float = 1.0
    comment: Optional[str] = None
    referenceDescription: Optional[str] = None
    unit: Optional[str] = None
    optional: bool = False
    component: Optional[ComponentDTO] = None
    cadInstances: List[CADInstanceDTO] = []
    substitutes: List[dict] = []
