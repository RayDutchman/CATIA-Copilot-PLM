"""DTO: PathChoiceDTO."""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class PathChoiceDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    resolvedPath: List["ResolvedPartLinkDTO"] = []
    partUsageLink: Optional[dict] = None


from app.schemas.baseline.resolved_part_link import ResolvedPartLinkDTO  # noqa: E402

PathChoiceDTO.model_rebuild()
