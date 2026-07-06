"""InstanceBooleanAttribute — 布尔型实例属性。"""
from app.models.meta.instance_attribute import InstanceAttribute
class InstanceBooleanAttribute(InstanceAttribute):
    __mapper_args__ = {"polymorphic_identity": "BOOLEAN"}
