"""DTO: EffectivityDTO — 统一的效果性 DTO，包含所有子类型的字段。"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class EffectivityDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    configurationItemKey: Optional["ConfigurationItemKeyDTO"] = None
    typeEffectivity: Optional[str] = None
    startNumber: Optional[str] = None
    endNumber: Optional[str] = None
    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None
    startLotId: Optional[str] = None
    endLotId: Optional[str] = None


from app.schemas.product.configuration_item_key import ConfigurationItemKeyDTO  # noqa: E402

EffectivityDTO.model_rebuild()
