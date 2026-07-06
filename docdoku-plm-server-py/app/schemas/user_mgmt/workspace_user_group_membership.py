"""DTO: WorkspaceUserGroupMembershipDTO. Auto-split from user_mgmt.py."""
from typing import Optional
from pydantic import BaseModel, ConfigDict


class WorkspaceUserGroupMembershipDTO(BaseModel):
    """用户组成员关系（/memberships/usergroups）"""
    model_config = ConfigDict(extra='forbid')
    workspaceId: str
    memberId: str
    readOnly: bool = False
    member: Optional[dict] = None
