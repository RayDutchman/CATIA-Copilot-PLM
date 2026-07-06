"""DTO: ProductInstanceIterationDTO. Auto-split from product.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from app.schemas.part import UserDTO


class ProductInstanceIterationDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    iteration: Optional[int] = None
    iterationNote: Optional[str] = None
    creationDate: Optional[str] = None
    modificationDate: Optional[str] = None
    author: Optional[UserDTO] = None
    productBaselineId: Optional[int] = None
