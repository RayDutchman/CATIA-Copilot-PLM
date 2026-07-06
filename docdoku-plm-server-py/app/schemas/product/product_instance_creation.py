"""DTO: ProductInstanceCreationDTO."""
from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class ProductInstanceCreationDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    serialNumber: Optional[str] = None
    configurationItemId: Optional[str] = None
    baselineId: Optional[int] = None
    acl: Optional[dict] = None
    instanceAttributes: List[dict] = []
    linkedDocuments: List[dict] = []
    attachedFiles: List[dict] = []
    type: Optional[str] = None
    effectiveDate: Optional[datetime] = None
    effectiveSerialNumber: Optional[str] = None
    effectiveLotId: Optional[str] = None
