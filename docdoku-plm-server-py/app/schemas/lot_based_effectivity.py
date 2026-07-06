"""DTO: LotBasedEffectivityDTO — 继承 EffectivityDTO。"""
from __future__ import annotations
from app.schemas.effectivity import EffectivityDTO


class LotBasedEffectivityDTO(EffectivityDTO):
    """基于批次的效性 DTO，额外字段已在父类 EffectivityDTO 中。"""
    pass
