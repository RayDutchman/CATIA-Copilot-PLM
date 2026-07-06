"""变更管理相关 Pydantic DTO，字段名与 DocdokuPLM JSON 响应完全一致（camelCase）。"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class AffectedPartDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    partKey: Optional[str] = None
    partNumber: Optional[str] = None
    version: Optional[str] = None


class AffectedDocumentDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    documentKey: Optional[str] = None
    documentMasterId: Optional[str] = None
    version: Optional[str] = None


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


class ChangeIssueDTO(ChangeItemDTO):
    initiator: Optional[str] = None


class ChangeRequestDTO(ChangeItemDTO):
    milestoneId: Optional[int] = None
    addressedChangeIssues: List[dict] = []


class ChangeOrderDTO(ChangeItemDTO):
    milestoneId: Optional[int] = None
    addressedChangeRequests: List[dict] = []


class MilestoneDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    dueDate: Optional[str] = None
    workspaceId: Optional[str] = None
    acl: Optional[dict] = None
    writable: Optional[bool] = None
    numberOfOrders: Optional[int] = None
    numberOfRequests: Optional[int] = None
