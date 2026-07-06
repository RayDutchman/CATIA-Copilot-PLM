"""InstanceTextAttribute — 文本型实例属性。"""
from app.models.meta.instance_attribute import InstanceAttribute
class InstanceTextAttribute(InstanceAttribute):
    __mapper_args__ = {"polymorphic_identity": "TEXT"}
