"""杂项 Pydantic DTO——webhook、通知、角色、标签、LOV、文件夹、组织、共享 等。"""
from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, ConfigDict

from app.schemas.part import UserDTO


# ============ Webhook ============

class WebhookAppDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    dtype: Optional[str] = None  # SIMPLE_HTTP / AWS_SNS
    uri: Optional[str] = None
    method: Optional[str] = None
    auth: Optional[str] = None


class WebhookDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: Optional[str] = None
    workspaceId: Optional[str] = None
    active: Optional[bool] = True
    appName: Optional[str] = None
    parameters: List[dict] = []
    webhookApp: Optional[WebhookAppDTO] = None


# ============ Notification ============

class ModificationNotificationDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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

class RoleDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[str] = None
    name: str
    workspaceId: Optional[str] = None
    defaultAssignedUsers: List[dict] = []
    defaultAssignedGroups: List[dict] = []


# ============ Tag ============

class TagDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    label: Optional[str] = None
    workspaceId: Optional[str] = None


# ============ LOV (List of Values) ============

class LOVValueDTO(BaseModel):
    name: Optional[str] = None
    value: Optional[str] = None


class LOVDTO(BaseModel):
    name: str
    id: Optional[str] = None
    workspaceId: Optional[str] = None
    values: List[LOVValueDTO] = []
    deletable: Optional[bool] = None


# ============ Attribute ============

class AttributeDTO(BaseModel):
    type: Optional[str] = None
    name: Optional[str] = None
    value: Optional[str] = None
    mandatory: Optional[bool] = None


# ============ Health ============

class HealthDTO(BaseModel):
    executionTime: int = 0
    status: str = "ok"


# ============ Language / Timezone ============

# 直接使用 list[str] 作为 response_model
# LanguageDTO = list[str]
# TimezoneDTO = list[str]


# ============ Folder ============

class FolderDTO(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    path: Optional[str] = None
    home: bool = False

    class Config:
        from_attributes = True


class FolderStatusDTO(BaseModel):
    status: str = "ok"


# ============ Organization ============

class OrganizationDTO(BaseModel):
    name: str
    description: Optional[str] = None


class OrganizationMemberResultDTO(BaseModel):
    status: str = "ok"


# ============ Share ============

class SharedDocumentDTO(BaseModel):
    id: Optional[str] = None
    workspaceId: Optional[str] = None
    version: Optional[str] = None
    type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    author: Optional[UserDTO] = None
    creationDate: Optional[str] = None


class SharedPartDTO(BaseModel):
    partNumber: Optional[str] = None
    version: Optional[str] = None
    workspaceId: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    author: Optional[UserDTO] = None
    creationDate: Optional[str] = None


# ============ Effectivity ============

class EffectivityDTO(BaseModel):
    """效应信息占位（当前实现返回 []）。"""
    pass


# ============ Platform Options ============

class PlatformOptionsDTO(BaseModel):
    workspaceCreationStrategy: str = "NONE"
    registrationStrategy: str = "NONE"


# ============ Workspace Workflow Instantiation ============

class WorkspaceWorkflowDTO(BaseModel):
    """workspace_workflow 实例化响应（instantiate / get detail）。"""
    id: Optional[str] = None
    workflowId: Optional[int] = None
    workspaceId: Optional[str] = None
    workflowModelId: Optional[str] = None
