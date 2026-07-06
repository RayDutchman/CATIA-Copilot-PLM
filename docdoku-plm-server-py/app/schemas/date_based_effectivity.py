"""DTO: DateBasedEffectivityDTO — 继承 EffectivityDTO。"""
from __future__ import annotations
from app.schemas.effectivity import EffectivityDTO


class DateBasedEffectivityDTO(EffectivityDTO):
    """基于日期的效果性 DTO，额外字段已在父类 EffectivityDTO 中。"""
    pass
