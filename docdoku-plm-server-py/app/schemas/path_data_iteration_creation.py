"""DTO: PathDataIterationCreationDTO."""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class PathDataIterationCreationDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    id: int = 0
    path: Optional[str] = None
    iteration: int = 0
    iterationNote: Optional[str] = None
    attachedFiles: List[str] = []
    linkedDocuments: List[dict] = []
    instanceAttributes: List[dict] = []
