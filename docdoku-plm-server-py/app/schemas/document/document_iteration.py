"""DTO: DocumentIterationDTO. Auto-split from document.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from app.schemas.part import UserDTO


class DocumentIterationDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: Optional[str] = None
    iteration: Optional[int] = None
    workspaceId: Optional[str] = None
    documentMasterId: Optional[str] = None
    documentRevisionVersion: Optional[str] = None
    version: Optional[str] = None
    title: Optional[str] = None
    revisionNote: Optional[str] = None
    creationDate: Optional[str] = None
    modificationDate: Optional[str] = None
    checkInDate: Optional[str] = None
    instanceAttributes: List[dict] = []
    attachedFiles: List[dict] = []
    linkedDocuments: List[dict] = []
    author: Optional[UserDTO] = None
    documentRevision: Optional[dict] = None
