"""DTO: PathDataIterationDTO."""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class PathDataIterationDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    serialNumber: Optional[str] = None
    pathDataMasterId: Optional[int] = None
    iteration: Optional[int] = None
    iterationNote: Optional[str] = None
    partLinksList: Optional[dict] = None
    path: Optional[str] = None
    attachedFiles: List[dict] = []
    linkedDocuments: List[dict] = []
    instanceAttributes: List[dict] = []
