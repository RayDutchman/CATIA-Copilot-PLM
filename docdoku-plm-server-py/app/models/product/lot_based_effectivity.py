"""LotBasedEffectivity ORM 模型 — 有效期基于批次号范围。"""
from app.models.product.effectivity import Effectivity


class LotBasedEffectivity(Effectivity):
    __mapper_args__ = {"polymorphic_identity": "LotBasedEffectivity"}
