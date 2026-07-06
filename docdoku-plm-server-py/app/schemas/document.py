"""文档相关 Pydantic DTO，字段名与 DocdokuPLM JSON 响应完全一致（camelCase）。"""
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
    routePath: Optional[str] = None
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


class BaselinedDocumentDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    documentMasterId: Optional[str] = None
    version: Optional[str] = None
    iteration: Optional[int] = None


class DocumentBaselineDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[int] = None
    creationDate: Optional[str] = None
    author: Optional[UserDTO] = None
    baselinedDocuments: List[BaselinedDocumentDTO] = []


class FolderDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: Optional[str] = None
    name: Optional[str] = None
    path: Optional[str] = None
    home: Optional[bool] = None
