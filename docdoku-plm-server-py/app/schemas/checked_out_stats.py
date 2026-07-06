"""DTO: CheckedOutStatsResponseDTO — mapping for checked out entities stats."""
from __future__ import annotations
from typing import Dict, List
from pydantic import BaseModel, ConfigDict


class CheckedOutStatsResponseDTO(BaseModel):
    """按用户和日期分组的检出统计数据。Java 原为 extends HashMap<String, List<Map<String, Long>>>"""
    model_config = ConfigDict(extra="allow")

    stats: Dict[str, List[Dict[str, int]]] = {}
