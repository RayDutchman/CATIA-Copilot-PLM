"""DTO: PartIterationDTO. Auto-split from part.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List


class PartIterationDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, exclude_none=True, extra='forbid')

    workspaceId: str
    number: str
    version: str
    iteration: int
    name: str = ""
    iterationNote: Optional[str] = None
    author: Optional[UserDTO] = None
    creationDate: Optional[datetime] = None
    modificationDate: Optional[datetime] = None
    checkInDate: Optional[datetime] = None
    instanceAttributes: List[dict] = []
    instanceAttributeTemplates: List[dict] = []
    nativeCADFile: Optional[BinaryResourceDTO] = None
    geometryFileURI: Optional[str] = None
    components: List[PartUsageLinkDTO] = []
    attachedFiles: List[BinaryResourceDTO] = []
    linkedDocuments: List[dict] = []
