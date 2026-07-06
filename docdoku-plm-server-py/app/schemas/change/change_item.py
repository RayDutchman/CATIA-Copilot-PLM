"""DTO: ChangeItemDTO. Auto-split from change.py."""
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class ChangeItemDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: Optional[int] = None
    name: Optional[str] = None
    workspaceId: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    author: Optional[str] = None
    authorName: Optional[str] = None
    assignee: Optional[str] = None
    assigneeName: Optional[str] = None
    creationDate: Optional[str] = None
    tags: List[str] = []
    acl: Optional[dict] = None
    writable: Optional[bool] = None
    affectedDocuments: List[AffectedDocumentDTO] = []
    affectedParts: List[AffectedPartDTO] = []
