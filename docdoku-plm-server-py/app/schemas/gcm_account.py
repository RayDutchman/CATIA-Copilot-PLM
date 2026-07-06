"""DTO: GCMAccountDTO."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict


class GCMAccountDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    login: str = ""
    gcmId: str = ""
