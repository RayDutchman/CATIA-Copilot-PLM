"""InstanceURLAttribute — URL 型实例属性。"""
from app.models.meta.instance_attribute import InstanceAttribute
class InstanceURLAttribute(InstanceAttribute):
    __mapper_args__ = {"polymorphic_identity": "URL"}
