"""DTO: WebhookDTO. Auto-split from misc.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class WebhookDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    id: int
    name: Optional[str] = None
    # 以下两字段为 Python 后端扩展（Java WebhookDTO 无 workspaceId/webhookApp），
    # 前端未使用，保守保留避免序列化兼容性问题。
    workspaceId: Optional[str] = None
    active: Optional[bool] = True
    appName: Optional[str] = None
    parameters: List[dict] = []
    webhookApp: Optional[WebhookAppDTO] = None


# ============ Notification ============
