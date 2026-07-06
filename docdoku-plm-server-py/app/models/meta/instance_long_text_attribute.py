"""InstanceLongTextAttribute — 长文本型实例属性。"""
from app.models.meta.instance_attribute import InstanceAttribute
class InstanceLongTextAttribute(InstanceAttribute):
    __mapper_args__ = {"polymorphic_identity": "LONGTEXT"}
