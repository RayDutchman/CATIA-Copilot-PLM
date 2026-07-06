"""DTO: DocumentTemplateDTO. Auto-split from document.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from app.schemas.part import UserDTO


class DocumentTemplateDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: Optional[str] = None
    workspaceId: Optional[str] = None
    documentType: Optional[str] = None
    mask: Optional[str] = None
    idGenerated: Optional[bool] = None
    attributesLocked: Optional[bool] = None
    creationDate: Optional[str] = None
    modificationDate: Optional[str] = None
    author: Optional[UserDTO] = None
    acl: Optional[dict] = None
    attributeTemplates: List[dict] = []
    attachedFiles: List[dict] = []
