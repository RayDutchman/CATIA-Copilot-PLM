"""DTO: DocumentRevisionDTO. Auto-split from document.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from app.schemas.part import UserDTO


class DocumentRevisionDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: Optional[str] = None
    version: Optional[str] = None
    workspaceId: Optional[str] = None
    documentMasterId: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    tags: List[str] = []
    path: Optional[str] = None
    routePath: list = []
    acl: Optional[dict] = None
    publicShared: bool = False
    attributesLocked: bool = False
    author: Optional[UserDTO] = None
    checkOutUser: Optional[UserDTO] = None
    checkOutDate: Optional[str] = None
    releaseAuthor: Optional[UserDTO] = None
    releaseDate: Optional[str] = None
    obsoleteAuthor: Optional[UserDTO] = None
    obsoleteDate: Optional[str] = None
    creationDate: Optional[str] = None
    lastIterationNumber: Optional[int] = None
    lastIteration: Optional[int] = None
    documentIterations: List[DocumentIterationDTO] = []
    iterationSubscription: bool = False
    stateSubscription: bool = False
    commentLink: Optional[str] = None
    workflow: Optional[dict] = None
    lifeCycleState: Optional[str] = None
    type: Optional[str] = None
