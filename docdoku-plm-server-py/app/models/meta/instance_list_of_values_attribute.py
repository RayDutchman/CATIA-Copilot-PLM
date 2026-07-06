"""InstanceListOfValuesAttribute — LOV 型实例属性。"""
from app.models.meta.instance_attribute import InstanceAttribute
class InstanceListOfValuesAttribute(InstanceAttribute):
    __mapper_args__ = {"polymorphic_identity": "LOV"}
