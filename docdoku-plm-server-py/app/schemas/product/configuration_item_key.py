"""DTO: ConfigurationItemKeyDTO."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional


class ConfigurationItemKeyDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    workspace: Optional[str] = None
    id: Optional[str] = None
