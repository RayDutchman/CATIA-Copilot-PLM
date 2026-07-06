"""DTO: OAuthLoginRequestDTO."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict


class OAuthLoginRequestDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    accessToken: Optional[str] = None
    idToken: Optional[str] = None
    state: Optional[str] = None
    tokenType: Optional[str] = None
    nonce: Optional[str] = None
    providerId: Optional[int] = None
