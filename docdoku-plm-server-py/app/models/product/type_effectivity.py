"""TypeEffectivity ORM 模型 — 有效期基于类型。"""
from app.models.product.effectivity import Effectivity


class TypeEffectivity(Effectivity):
    __mapper_args__ = {"polymorphic_identity": "type"}
