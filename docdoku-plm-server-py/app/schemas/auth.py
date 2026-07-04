"""认证相关 Pydantic schemas。字段名与 DocdokuPLM AccountDTO 保持一致。"""
from pydantic import BaseModel
from typing import Optional

class LoginRequestDTO(BaseModel):
    login: str
    password: str

class AccountDTO(BaseModel):
    login: str
    email: str
    name: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    admin: bool = False

    class Config:
        from_attributes = True
