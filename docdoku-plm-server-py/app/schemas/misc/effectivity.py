"""DTO: EffectivityDTO. Auto-split from misc.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class EffectivityDTO(BaseModel):
    """有效性信息（对齐 Payara EffectivityDTO + effectivity 路由实际输出形状）。

    typeEffectivity 取值：SERIALNUMBERBASEDEFFECTIVITY / DATEBASEDEFFECTIVITY / LOTBASEDEFFECTIVITY。
    按类型带不同的起止字段（date / number / lot）。
    """
    model_config = ConfigDict(extra='forbid')

    id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    configurationItemNumber: Optional[str] = None
    workspaceId: Optional[str] = None
    typeEffectivity: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    startNumber: Optional[str] = None
    endNumber: Optional[str] = None
    startLotId: Optional[str] = None
    endLotId: Optional[str] = None


# ============ Platform Options ============
