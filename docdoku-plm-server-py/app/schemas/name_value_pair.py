"""DTO: NameValuePairDTO."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict


class NameValuePairDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    name: Optional[str] = None
    value: Optional[str] = None
