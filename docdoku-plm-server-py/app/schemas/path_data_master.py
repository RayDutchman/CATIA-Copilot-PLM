"""DTO: PathDataMasterDTO."""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class PathDataMasterDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: Optional[int] = None
    path: Optional[str] = None
    serialNumber: Optional[str] = None
    partLinksList: Optional[dict] = None
    pathDataIterations: List["PathDataIterationDTO"] = []
    partAttributes: List[dict] = []
    partAttributeTemplates: List[dict] = []


from app.schemas.path_data_iteration import PathDataIterationDTO  # noqa: E402

PathDataMasterDTO.model_rebuild()
