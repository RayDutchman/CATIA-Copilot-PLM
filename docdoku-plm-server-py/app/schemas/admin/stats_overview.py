"""DTO: StatsOverviewDTO. Auto-split from admin.py."""
from pydantic import BaseModel, ConfigDict


class StatsOverviewDTO(BaseModel):
    """工作区统计概览"""
    model_config = ConfigDict(extra='forbid')
    parts: int = 0
    documents: int = 0
    users: int = 0
    products: int = 0
    checkedOutDocuments: int = 0
    checkedOutParts: int = 0
