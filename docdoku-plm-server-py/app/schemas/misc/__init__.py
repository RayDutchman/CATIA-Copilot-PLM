"""杂项 Pydantic DTO——webhook、通知、角色、标签、LOV、文件夹、组织、共享 等。"""
from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class FolderDTO(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    path: Optional[str] = None
    home: bool = False

    model_config = ConfigDict(from_attributes=True, extra='forbid')



class FolderStatusDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: str = "ok"


# ============ Organization ============


class HealthDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    executionTime: int = 0
    status: str = "ok"


# ============ Language / Timezone ============

# 直接使用 list[str] 作为 response_model
# LanguageDTO = list[str]
# TimezoneDTO = list[str]


# ============ Folder ============


class LOVValueDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: Optional[str] = None
    value: Optional[str] = None



class OrganizationMemberResultDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: str = "ok"


# ============ Share ============


class PlatformOptionsDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    workspaceCreationStrategy: str = "NONE"
    registrationStrategy: str = "NONE"


# ============ Workspace Workflow Instantiation ============


class WorkspaceWorkflowDTO(BaseModel):
    """workspace_workflow 实例化响应（instantiate / get detail）。"""
    model_config = ConfigDict(extra='forbid')
    id: Optional[str] = None
    workflowId: Optional[int] = None
    workspaceId: Optional[str] = None
    workflowModelId: Optional[str] = None


from app.schemas.part import UserDTO


# ============ Webhook ============

# Re-exports from split files
from app.schemas.misc.webhook_app_parameter import WebhookAppDTO  # noqa: E402, F401
from app.schemas.misc.webhook import WebhookDTO  # noqa: E402, F401
from app.schemas.misc.modification_notification import ModificationNotificationDTO  # noqa: E402, F401
from app.schemas.misc.role import RoleDTO  # noqa: E402, F401
from app.schemas.misc.tag import TagDTO  # noqa: E402, F401
from app.schemas.misc.list_of_values import LOVDTO  # noqa: E402, F401
from app.schemas.misc.instance_attribute import AttributeDTO  # noqa: E402, F401
from app.schemas.misc.organization import OrganizationDTO  # noqa: E402, F401
from app.schemas.misc.shared_document import SharedDocumentDTO  # noqa: E402, F401
from app.schemas.misc.shared_part import SharedPartDTO  # noqa: E402, F401
from app.schemas.misc.effectivity import EffectivityDTO  # noqa: E402, F401

UserDTO.model_rebuild()
WebhookAppDTO.model_rebuild()
WebhookDTO.model_rebuild()
ModificationNotificationDTO.model_rebuild()
RoleDTO.model_rebuild()
TagDTO.model_rebuild()
LOVDTO.model_rebuild()
AttributeDTO.model_rebuild()
OrganizationDTO.model_rebuild()
SharedDocumentDTO.model_rebuild()
SharedPartDTO.model_rebuild()
EffectivityDTO.model_rebuild()
