"""DTO: ProductBaselineSummaryDTO. Auto-split from product.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from app.schemas.part import UserDTO


class ProductBaselineSummaryDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: Optional[int] = None
    name: Optional[str] = None
    type: Optional[int] = None
    configurationItemId: Optional[str] = None
    author: Optional[UserDTO] = None
    creationDate: Optional[str] = None
    description: Optional[str] = None
    hasObsoletePartRevisions: bool = False
    configurationItemLatestRevision: Optional[ConfigurationItemLatestRevisionDTO] = None
    baselinedParts: List[BaselinedPartDTO] = []
    substituteLinks: List[dict] = []
    optionalUsageLinks: List[dict] = []
    pathToPathLinks: List[dict] = []
    substitutesParts: List[dict] = []
    optionalsParts: List[dict] = []
