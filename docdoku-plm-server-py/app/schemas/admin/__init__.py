"""管理员相关 Pydantic DTO，字段名与 DocdokuPLM JSON 响应保持一致（camelCase）。"""
from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class AdminAccountDTO(BaseModel):
    """管理员视图的账户信息（含 workspaceId/admin 字段）"""
    model_config = ConfigDict(extra='forbid')
    login: str
    email: Optional[str] = None
    name: Optional[str] = None
    language: Optional[str] = None
    enabled: Optional[bool] = True
    workspaceId: Optional[str] = None
    admin: Optional[bool] = False



class BackOptionsDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    sendEmails: bool = False
    workspaceId: Optional[str] = None



class CheckedOutStatsDTO(BaseModel):
    """checked-out 统计（按用户分组）"""
    model_config = ConfigDict(extra='forbid')
    pass  # 实际是 dict[str, list[dict]], Pydantic 不支持动态 key, 返回 dict


class FrontOptionsDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    documentTableColumns: List[str] = []
    partTableColumns: List[str] = []



class IndexStatusDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    inProgress: bool = False
    status: Optional[str] = None
    note: Optional[str] = None



class PlatformOptionsDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    workspaceCreationStrategy: str = "NONE"
    registrationStrategy: str = "NONE"



class ReachableUserDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    login: str
    name: Optional[str] = None
    email: Optional[str] = None



class WorkspaceListDTO(BaseModel):
    """工作区列表（/workspaces）"""
    model_config = ConfigDict(extra='forbid')
    administratedWorkspaces: List[dict] = []
    allWorkspaces: List[dict] = []



# Re-exports from split files
from app.schemas.admin.workspace import WorkspaceDTO  # noqa: E402, F401
from app.schemas.admin.stats_overview import StatsOverviewDTO  # noqa: E402, F401
from app.schemas.admin.disk_usage_space import DiskUsageDTO  # noqa: E402, F401

WorkspaceDTO.model_rebuild()
StatsOverviewDTO.model_rebuild()
DiskUsageDTO.model_rebuild()
