"""DateBasedEffectivity ORM 模型 — 有效期基于日期范围。"""
from app.models.product.effectivity import Effectivity


class DateBasedEffectivity(Effectivity):
    __mapper_args__ = {"polymorphic_identity": "date_based"}
