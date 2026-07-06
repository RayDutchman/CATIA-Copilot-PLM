"""DTO: WebhookAppDTO. Auto-split from misc.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class WebhookAppDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    id: Optional[int] = None
    dtype: Optional[str] = None  # SIMPLE_HTTP / AWS_SNS
    uri: Optional[str] = None
    method: Optional[str] = None
    auth: Optional[str] = None
