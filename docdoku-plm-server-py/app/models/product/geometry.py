"""Geometry ORM 模型。继承 BinaryResource 的 SINGLE_TABLE 映射，存储 GLB 几何体元数据。"""
from app.models.part import BinaryResource


class Geometry(BinaryResource):
    """对应 geometry 表（SINGLE_TABLE 继承自 binaryresource），
    由 dtype 列区分。quality 和包围盒已在父类 BinaryResource 中。"""
    __mapper_args__ = {"polymorphic_identity": "geometry"}
