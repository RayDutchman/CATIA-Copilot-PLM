"""DTO: DiskUsageDTO. Auto-split from admin.py."""
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DiskUsageDTO(BaseModel):
    """工作区磁盘使用统计"""
    model_config = ConfigDict(extra='forbid')
    documents: int = 0
    parts: int = 0
    partTemplates: int = 0
    documentTemplates: int = 0
    total: Optional[int] = None
