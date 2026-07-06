"""认证相关 Pydantic schemas。字段名与 DocdokuPLM AccountDTO 保持一致。"""
from pydantic import BaseModel, ConfigDict
from typing import Optional

class LoginRequestDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    login: str
    password: str

class AccountDTO(BaseModel):
    login: str
    email: str
    name: Optional[str] = None
    language: Optional[str] = None
    timeZone: Optional[str] = None
    enabled: Optional[bool] = None
    admin: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True, extra='forbid')
