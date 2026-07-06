"""DTO: WorkspaceMembershipDTO. Auto-split from user_mgmt.py."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict


class WorkspaceMembershipDTO(BaseModel):
    """用户成员关系（/memberships/users）"""
    model_config = ConfigDict(extra='forbid')
    workspaceId: str
    member: UserDTO
    readOnly: bool = False
    permission: Optional[str] = None
