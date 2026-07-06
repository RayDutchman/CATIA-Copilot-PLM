"""InstanceNumberAttribute — 数字型实例属性。"""
from app.models.meta.instance_attribute import InstanceAttribute
class InstanceNumberAttribute(InstanceAttribute):
    __mapper_args__ = {"polymorphic_identity": "NUMBER"}
