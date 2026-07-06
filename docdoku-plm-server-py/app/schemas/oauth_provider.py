"""DTO: OAuthProviderDTO — extends OAuthProviderPublicDTO."""
from __future__ import annotations
from typing import Optional
from app.schemas.oauth_provider_public import OAuthProviderPublicDTO


class OAuthProviderDTO(OAuthProviderPublicDTO):
    secret: Optional[str] = None
