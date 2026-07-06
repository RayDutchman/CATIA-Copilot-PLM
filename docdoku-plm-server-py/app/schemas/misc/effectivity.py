"""DTO: EffectivityDTO. Auto-split from misc.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class EffectivityDTO(BaseModel):
    """效应信息占位（当前实现返回 []）。"""
    model_config = ConfigDict(extra='forbid')
    pass


# ============ Platform Options ============
