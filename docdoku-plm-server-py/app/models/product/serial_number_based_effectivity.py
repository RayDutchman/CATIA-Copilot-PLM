"""SerialNumberBasedEffectivity ORM 模型 — 有效期基于序列号范围。"""
from app.models.product.effectivity import Effectivity


class SerialNumberBasedEffectivity(Effectivity):
    __mapper_args__ = {"polymorphic_identity": "SerialNumberBasedEffectivity"}
