"""认证相关 Pydantic schemas。字段名与 DocdokuPLM AccountDTO 保持一致。"""
from pydantic import BaseModel, ConfigDict
from typing import Optional

# Re-exports from split files
from app.schemas.auth.account import AccountDTO  # noqa: E402, F401
from app.schemas.auth.login_request import LoginRequestDTO  # noqa: E402, F401

AccountDTO.model_rebuild()
LoginRequestDTO.model_rebuild()
