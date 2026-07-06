"""管理员相关 Pydantic DTO，字段名与 DocdokuPLM JSON 响应保持一致（camelCase）。"""
from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class WorkspaceDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    description: Optional[str] = None
    enabled: Optional[bool] = True
    folderLocked: Optional[bool] = False
    admin: Optional[str] = None
    creationDate: Optional[str] = None


class StatsOverviewDTO(BaseModel):
    """工作区统计概览"""
    parts: int = 0
    documents: int = 0
    users: int = 0
    products: int = 0
    checkedOutDocuments: int = 0
    checkedOutParts: int = 0


class DiskUsageDTO(BaseModel):
    """工作区磁盘使用统计"""
    documents: int = 0
    parts: int = 0
    partTemplates: int = 0
    documentTemplates: int = 0
    total: Optional[int] = None


class FrontOptionsDTO(BaseModel):
    documentTableColumns: List[str] = []
    partTableColumns: List[str] = []


class BackOptionsDTO(BaseModel):
    sendEmails: bool = False
    workspaceId: Optional[str] = None


class ReachableUserDTO(BaseModel):
    login: str
    name: Optional[str] = None
    email: Optional[str] = None


class WorkspaceListDTO(BaseModel):
    """工作区列表（/workspaces）"""
    administratedWorkspaces: List[dict] = []
    allWorkspaces: List[dict] = []


class AdminAccountDTO(BaseModel):
    """管理员视图的账户信息（含 workspaceId/admin 字段）"""
    login: str
    email: Optional[str] = None
    name: Optional[str] = None
    language: Optional[str] = None
    enabled: Optional[bool] = True
    workspaceId: Optional[str] = None
    admin: Optional[bool] = False


class PlatformOptionsDTO(BaseModel):
    workspaceCreationStrategy: str = "NONE"
    registrationStrategy: str = "NONE"


class IndexStatusDTO(BaseModel):
    inProgress: bool = False
    status: Optional[str] = None
    note: Optional[str] = None


class CheckedOutStatsDTO(BaseModel):
    """checked-out 统计（按用户分组）"""
    pass  # 实际是 dict[str, list[dict]], Pydantic 不支持动态 key, 返回 dict
