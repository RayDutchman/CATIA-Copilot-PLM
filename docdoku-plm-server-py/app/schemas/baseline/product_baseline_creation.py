"""DTO: ProductBaselineCreationDTO."""
from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class ProductBaselineCreationDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    name: Optional[str] = None
    description: Optional[str] = None
    configurationItemId: Optional[str] = None
    type: Optional[str] = None
    baselinedParts: List["BaselinedPartDTO"] = []
    substituteLinks: List[str] = []
    optionalUsageLinks: List[str] = []
    effectiveDate: Optional[datetime] = None
    effectiveSerialNumber: Optional[str] = None
    effectiveLotId: Optional[str] = None


from app.schemas.baseline.baselined_part import BaselinedPartDTO  # noqa: E402

ProductBaselineCreationDTO.model_rebuild()
