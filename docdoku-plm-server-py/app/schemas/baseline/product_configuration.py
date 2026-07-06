"""DTO: ProductConfigurationDTO."""
from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class ProductConfigurationDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: Optional[int] = None
    configurationItemId: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    substituteLinks: List[str] = []
    optionalUsageLinks: List[str] = []
    creationDate: Optional[datetime] = None
    author: Optional[dict] = None
    substitutesParts: List[dict] = []
    optionalsParts: List[dict] = []
    acl: Optional[dict] = None
