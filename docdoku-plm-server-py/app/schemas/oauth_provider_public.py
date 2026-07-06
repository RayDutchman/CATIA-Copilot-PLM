"""DTO: OAuthProviderPublicDTO."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict


class OAuthProviderPublicDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: Optional[int] = None
    name: Optional[str] = None
    enabled: bool = False
    issuer: Optional[str] = None
    clientID: Optional[str] = None
    jwsAlgorithm: Optional[str] = None
    jwkSetURL: Optional[str] = None
    redirectUri: Optional[str] = None
    authority: Optional[str] = None
    scope: Optional[str] = None
    responseType: Optional[str] = None
    authorizationEndpoint: Optional[str] = None
    signingKeys: Optional[str] = None
