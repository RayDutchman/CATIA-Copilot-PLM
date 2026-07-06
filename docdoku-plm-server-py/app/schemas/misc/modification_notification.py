"""DTO: ModificationNotificationDTO. Auto-split from misc.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from app.schemas.part import UserDTO


class ModificationNotificationDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    id: int
    acknowledged: Optional[bool] = None
    ackComment: Optional[str] = None
    ackAuthor: Optional[UserDTO] = None
    ackDate: Optional[int] = None
    impactedPartNumber: Optional[str] = None
    impactedPartVersion: Optional[str] = None
    modifiedPartNumber: Optional[str] = None
    modifiedPartVersion: Optional[str] = None
    modifiedPartIteration: Optional[int] = None
    modifiedPartName: Optional[str] = None
    checkInDate: Optional[int] = None
    author: Optional[UserDTO] = None
    iterationNote: Optional[str] = None


# ============ Role ============
