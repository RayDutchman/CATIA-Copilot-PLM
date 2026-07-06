"""用户管理相关 Pydantic DTO，字段名与 DocdokuPLM JSON 响应保持一致（camelCase）。"""
from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, ConfigDict

from app.schemas.part import UserDTO


class UserDTOExtended(UserDTO):
    """扩展 UserDTO，增加 admin/timeZone 字段（accounts/me 等端点使用）"""
    model_config = ConfigDict(from_attributes=True, extra='forbid')
    admin: Optional[bool] = None
    timeZone: Optional[str] = None


class UserGroupDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    id: str
    workspaceId: Optional[str] = None


class UserGroupMemberDTO(BaseModel):
    """工作组内用户信息"""
    model_config = ConfigDict(extra='forbid')
    login: str
    name: Optional[str] = None
    email: Optional[str] = None
    language: Optional[str] = None


class WorkspaceMembershipDTO(BaseModel):
    """用户成员关系（/memberships/users）"""
    model_config = ConfigDict(extra='forbid')
    workspaceId: str
    member: UserDTO
    readOnly: bool = False
    permission: Optional[str] = None


class WorkspaceUserGroupMembershipDTO(BaseModel):
    """用户组成员关系（/memberships/usergroups）"""
    model_config = ConfigDict(extra='forbid')
    workspaceId: str
    memberId: str
    readOnly: bool = False
    member: Optional[dict] = None


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


class TagSubscriptionDTO(BaseModel):
    """Tag 订阅响应"""
    model_config = ConfigDict(extra='forbid')
    tag: str
    onIterationChange: bool = False
    onStateChange: bool = False


class WorkspaceInfoDTO(BaseModel):
    """用户工作区简要信息（/accounts/workspaces）"""
    model_config = ConfigDict(extra='forbid')
    id: str
    description: Optional[str] = None
    enabled: Optional[bool] = True
    folderLocked: Optional[bool] = False


class AccountStatsDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    totalAccounts: int = 0
    enabledAccounts: int = 0
    disabledAccounts: int = 0


class WorkspaceStatsDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    totalWorkspaces: int = 0
    enabledWorkspaces: int = 0
