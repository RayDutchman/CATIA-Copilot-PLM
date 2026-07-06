"""DTO: PasswordRecoverDTO."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict


class PasswordRecoverDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    uuid: str
    newPassword: str
