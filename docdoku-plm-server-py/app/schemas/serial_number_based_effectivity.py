"""DTO: SerialNumberBasedEffectivityDTO — 继承 EffectivityDTO。"""
from __future__ import annotations
from app.schemas.effectivity import EffectivityDTO


class SerialNumberBasedEffectivityDTO(EffectivityDTO):
    """基于序列号的效果性 DTO，额外字段已在父类 EffectivityDTO 中。"""
    pass
