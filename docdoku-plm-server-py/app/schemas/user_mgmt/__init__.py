"""用户管理相关 Pydantic DTO，字段名与 DocdokuPLM JSON 响应保持一致（camelCase）。"""
from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class AccountStatsDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    totalAccounts: int = 0
    enabledAccounts: int = 0
    disabledAccounts: int = 0



class TagSubscriptionDTO(BaseModel):
    """Tag 订阅响应"""
    model_config = ConfigDict(extra='forbid')
    tag: str
    onIterationChange: bool = False
    onStateChange: bool = False



class UserGroupMemberDTO(BaseModel):
    """工作组内用户信息"""
    model_config = ConfigDict(extra='forbid')
    login: str
    name: Optional[str] = None
    email: Optional[str] = None
    language: Optional[str] = None



class UserStatsDTO(BaseModel):
    """用户统计（/users-stats）"""
    model_config = ConfigDict(extra='forbid')
    users: int = 0
    activeusers: int = 0
    inactiveusers: int = 0
    groups: int = 0
    activegroups: int = 0
    inactivegroups: int = 0



class WorkspaceAdminDTO(BaseModel):
    """工作区管理员信息"""
    model_config = ConfigDict(extra='forbid')
    login: str
    name: Optional[str] = None
    email: Optional[str] = None
    language: Optional[str] = None
    workspaceId: Optional[str] = None



class WorkspaceInfoDTO(BaseModel):
    """用户工作区简要信息（/accounts/workspaces）"""
    model_config = ConfigDict(extra='forbid')
    id: str
    description: Optional[str] = None
    enabled: Optional[bool] = True
    folderLocked: Optional[bool] = False



class WorkspaceStatsDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    totalWorkspaces: int = 0
    enabledWorkspaces: int = 0


from app.schemas.part import UserDTO


class UserDTOExtended(UserDTO):
    """扩展 UserDTO，增加 admin/timeZone 字段（accounts/me 等端点使用）"""
    model_config = ConfigDict(from_attributes=True, extra='forbid')
    admin: Optional[bool] = None
    timeZone: Optional[str] = None

# Re-exports from split files
from app.schemas.user_mgmt.user_group import UserGroupDTO  # noqa: E402, F401
from app.schemas.user_mgmt.workspace_user_group_membership import WorkspaceUserGroupMembershipDTO  # noqa: E402, F401
from app.schemas.user_mgmt.workspace_user_membership import WorkspaceMembershipDTO  # noqa: E402, F401

UserDTO.model_rebuild()
UserGroupDTO.model_rebuild()
WorkspaceUserGroupMembershipDTO.model_rebuild()
WorkspaceMembershipDTO.model_rebuild()
