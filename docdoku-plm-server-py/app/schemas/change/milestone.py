"""DTO: MilestoneDTO. Auto-split from change.py."""
from typing import Optional
from pydantic import BaseModel, ConfigDict


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
