"""ProductConfigSpec 抽象基类。

用于为每个 PartMaster 选择正确的 PartIteration，
同时从完整的 PartLink 路径中筛选出应被考虑的那一条。
ProductConfigSpec 是 ProductStructureFilter 的严格版本——始终返回单值（最多1个）。
"""
from typing import List, Optional, Set
from app.models.configuration.product_structure_filter import ProductStructureFilter


class ProductConfigSpec(ProductStructureFilter):
    """配置规格抽象基类。

    子类必须实现：
      - filter_part_iteration(part_master) -> Optional[PartIteration]
      - filter_part_link(path) -> Optional[PartLink]
    """

    def __init__(self):
        self.retained_part_iterations: Set = set()
        self.retained_substitute_links: Set[str] = set()
        self.retained_optional_usage_links: Set[str] = set()

    def filter_part_iterations(self, part_master) -> list:
        """final — 严格模式：最多返回1个 PartIteration。"""
        pi = self.filter_part_iteration(part_master)
        return [pi] if pi is not None else []

    def filter_links(self, path: list) -> list:
        """final — 严格模式：最多返回1个 PartLink。"""
        plink = self.filter_part_link(path)
        return [plink] if plink is not None else []

    def filter_part_iteration(self, part_master):
        """子类实现：返回单个 PartIteration 或 None。"""
        raise NotImplementedError

    def filter_part_link(self, path: list):
        """子类实现：返回单个 PartLink 或 None。"""
        raise NotImplementedError
