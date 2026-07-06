"""DTO: WebhookDTO. Auto-split from misc.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class WebhookDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    id: int
    name: Optional[str] = None
    workspaceId: Optional[str] = None
    active: Optional[bool] = True
    appName: Optional[str] = None
    parameters: List[dict] = []
    webhookApp: Optional[WebhookAppDTO] = None


# ============ Notification ============
