"""DTO: PasswordRecoveryRequestDTO."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict


class PasswordRecoveryRequestDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    login: str
