"""DTO: ProductInstanceDTO. Auto-split from product.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class ProductInstanceDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    serialNumber: Optional[str] = None
    workspaceId: Optional[str] = None
    configurationItemId: Optional[str] = None
    identifier: Optional[str] = None
    acl: Optional[dict] = None
    productInstanceIterations: List[ProductInstanceIterationDTO] = []
