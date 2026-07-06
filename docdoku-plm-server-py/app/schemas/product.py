"""产品相关 Pydantic DTO，字段名与 DocdokuPLM JSON 响应完全一致（camelCase）。"""
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


class BaselinedPartDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    partNumber: Optional[str] = None
    version: Optional[str] = None
    iteration: Optional[int] = None


class ConfigurationItemLatestRevisionDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    partNumber: Optional[str] = None
    version: Optional[str] = None
    status: Optional[int] = None


class ProductBaselineSummaryDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: Optional[int] = None
    name: Optional[str] = None
    type: Optional[int] = None
    configurationItemId: Optional[str] = None
    author: Optional[UserDTO] = None
    creationDate: Optional[str] = None
    description: Optional[str] = None
    hasObsoletePartRevisions: bool = False
    configurationItemLatestRevision: Optional[ConfigurationItemLatestRevisionDTO] = None
    baselinedParts: List[BaselinedPartDTO] = []
    substituteLinks: List[dict] = []
    optionalUsageLinks: List[dict] = []
    pathToPathLinks: List[dict] = []
    substitutesParts: List[dict] = []
    optionalsParts: List[dict] = []


class ProductBaselineDetailDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: Optional[int] = None
    name: Optional[str] = None
    type: Optional[int] = None
    configurationItemId: Optional[str] = None
    configurationItemWorkspaceId: Optional[str] = None
    creationDate: Optional[str] = None
    description: Optional[str] = None
    author: Optional[UserDTO] = None
    baselinedParts: List[BaselinedPartDTO] = []
    substituteLinks: List[dict] = []
    optionalUsageLinks: List[dict] = []
    pathToPathLinks: List[dict] = []
    substitutesParts: List[dict] = []
    optionalsParts: List[dict] = []


class ProductConfigurationDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: Optional[int] = None
    name: Optional[str] = None
    configurationItemId: Optional[str] = None
    description: Optional[str] = None
    author: Optional[UserDTO] = None
    acl: Optional[dict] = None
    creationDate: Optional[str] = None
    substituteLinks: List[dict] = []
    optionalUsageLinks: List[dict] = []
    substitutesParts: List[dict] = []
    optionalsParts: List[dict] = []


class ProductInstanceIterationDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    iteration: Optional[int] = None
    iterationNote: Optional[str] = None
    creationDate: Optional[str] = None
    modificationDate: Optional[str] = None
    author: Optional[UserDTO] = None
    productBaselineId: Optional[int] = None


class ProductInstanceDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    serialNumber: Optional[str] = None
    workspaceId: Optional[str] = None
    configurationItemId: Optional[str] = None
    identifier: Optional[str] = None
    acl: Optional[dict] = None
    productInstanceIterations: List[ProductInstanceIterationDTO] = []


class LayerDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: Optional[int] = None
    name: Optional[str] = None
    color: Optional[str] = None
    workspaceId: Optional[str] = None
    configurationItemId: Optional[str] = None


class MarkerDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: Optional[int] = None
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    title: Optional[str] = None
    description: Optional[str] = None
    layerId: Optional[int] = None
