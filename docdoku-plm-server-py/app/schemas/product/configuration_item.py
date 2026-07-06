"""DTO: ConfigurationItemDTO. Auto-split from product.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from app.schemas.part import UserDTO


class ConfigurationItemDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: Optional[str] = None
    workspaceId: Optional[str] = None
    description: Optional[str] = None
    designItemNumber: Optional[str] = None
    designItemName: Optional[str] = None
    designItemLatestVersion: Optional[str] = None
    author: Optional[UserDTO] = None
    creationDate: Optional[str] = None
    hasModificationNotification: bool = False
    pathToPathLinks: List[dict] = []
