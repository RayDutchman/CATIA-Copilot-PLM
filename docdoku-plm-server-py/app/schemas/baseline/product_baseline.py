"""DTO: ProductBaselineDTO."""
from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class ProductBaselineDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    creationDate: Optional[datetime] = None
    configurationItemId: Optional[str] = None
    configurationItemLatestRevision: Optional[str] = None
    type: Optional[str] = None
    baselinedParts: List["BaselinedPartDTO"] = []
    substituteLinks: List[str] = []
    optionalUsageLinks: List[str] = []
    substitutesParts: List[dict] = []
    optionalsParts: List[dict] = []
    author: Optional[dict] = None
    hasObsoletePartRevisions: bool = False
    pathToPathLinks: List["PathToPathLinkDTO"] = []


from app.schemas.baseline.baselined_part import BaselinedPartDTO  # noqa: E402
from app.schemas.path_to_path_link import PathToPathLinkDTO  # noqa: E402

ProductBaselineDTO.model_rebuild()
