"""DTO: AccountDTO. Auto-split from auth.py."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AccountDTO(BaseModel):
    login: str
    email: str
    name: Optional[str] = None
    language: Optional[str] = None
    timeZone: Optional[str] = None
    enabled: Optional[bool] = None
    admin: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True, extra='forbid')
