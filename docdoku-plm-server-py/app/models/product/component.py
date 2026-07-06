"""Component DTO 模型。非数据库实体，用于构建产品结构树。"""
from typing import List, Optional


class Component:
    """组装产品结构树的便利类（对应 Java Component DTO）。"""

    def __init__(self, part_master=None, retained_iteration=None, path=None, is_virtual=False):
        self.part_master = part_master
        self.retained_iteration = retained_iteration
        self.path = path or []
        self.components: List["Component"] = []
        self.is_virtual = is_virtual

    def add_component(self, child: "Component") -> None:
        self.components.append(child)

    @property
    def part_link(self):
        if self.path:
            return self.path[-1]
        return None
