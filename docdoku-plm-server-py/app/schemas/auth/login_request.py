"""DTO: LoginRequestDTO. Auto-split from auth.py."""
from pydantic import BaseModel, ConfigDict
from typing import Optional


class LoginRequestDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    login: str
    password: str
