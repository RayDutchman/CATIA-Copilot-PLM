"""DTO: PartRevisionDTO. Auto-split from part.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict, model_validator
from datetime import datetime
from typing import Optional, List


class PartRevisionDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, exclude_none=False, extra='forbid')

    workspaceId: str
    number: str
    version: str
    partKey: str = ""
    name: str = ""
    type: Optional[str] = None
    standardPart: bool = False
    author: Optional[UserDTO] = None
    creationDate: Optional[datetime] = None
    modificationDate: Optional[datetime] = None
    checkInDate: Optional[datetime] = None
    description: str = ""
    lastIterationNumber: int = 0
    partIterations: List[PartIterationDTO] = []
    checkOutUser: Optional[UserDTO] = None
    checkOutDate: Optional[datetime] = None
    status: Optional[str] = None
    tags: List[str] = []
    workflow: Optional[dict] = None
    lifeCycleState: Optional[str] = None
    acl: Optional[dict] = None
    publicShared: bool = False
    attributesLocked: bool = False
    releaseDate: Optional[datetime] = None
    releaseAuthor: Optional[UserDTO] = None
    obsoleteDate: Optional[datetime] = None
    obsoleteAuthor: Optional[UserDTO] = None
    notifications: List[dict] = []

    @model_validator(mode="after")
    def set_part_key(self) -> "PartRevisionDTO":
        if not self.partKey:
            self.partKey = f"{self.number}-{self.version}"
        return self
