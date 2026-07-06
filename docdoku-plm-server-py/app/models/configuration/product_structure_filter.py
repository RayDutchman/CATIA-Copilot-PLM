"""ProductStructureFilter 抽象基类。

产品结构过滤器接口。所有过滤器（ConfigSpec 和 PSFilter）都实现此接口。
"""
from typing import List


class ProductStructureFilter:
    """过滤器接口。

    两个抽象方法：
      - filter_part_iterations(part_master) -> List[PartIteration]
      - filter_links(path: List[PartLink]) -> List[PartLink]
    """

    def filter_part_iterations(self, part_master) -> list:
        """对 PartMaster 过滤，返回应使用的 PartIteration 列表（可能为空/1个/多个）。"""
        raise NotImplementedError

    def filter_links(self, path: list) -> list:
        """对路径末尾的 PartLink 过滤，返回应使用的 PartLink 列表。"""
        raise NotImplementedError
