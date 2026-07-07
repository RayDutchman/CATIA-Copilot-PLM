"""属性持有者接口（对标 AttributesHolder — 标记可持有属性的实体）。"""
from abc import ABC


class AttributesHolder(ABC):
    """标记接口：实现此类的 DTO 可持有 ImportAttribute 列表。"""
    pass
