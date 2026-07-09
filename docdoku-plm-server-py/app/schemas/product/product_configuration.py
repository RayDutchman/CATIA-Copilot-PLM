"""DTO: ProductConfigurationDTO. Auto-split from product.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from app.schemas.part import UserDTO


class ProductConfigurationDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: Optional[int] = None
    name: Optional[str] = None
    configurationItemId: Optional[str] = None
    description: Optional[str] = None
    author: Optional[UserDTO] = None
    acl: Optional[dict] = None
    creationDate: Optional[str] = None
    substituteLinks: List[str] = []
    optionalUsageLinks: List[str] = []
    substitutesParts: List[dict] = []
    optionalsParts: List[dict] = []
