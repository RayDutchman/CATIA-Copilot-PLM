"""InstanceDateAttribute — 日期型实例属性。"""
from app.models.meta.instance_attribute import InstanceAttribute
class InstanceDateAttribute(InstanceAttribute):
    __mapper_args__ = {"polymorphic_identity": "DATE"}
