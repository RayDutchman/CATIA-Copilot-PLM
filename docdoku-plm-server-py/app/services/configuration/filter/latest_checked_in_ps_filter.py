"""LatestCheckedInPSFilter——最新检入迭代过滤器。"""
from app.models.configuration.product_structure_filter import ProductStructureFilter


class LatestCheckedInPSFilter(ProductStructureFilter):
    """取最新修订版中最近检入的迭代。

    对齐 Java LatestCheckedInPSFilter。严格单结果（最多1个）。
    """

    def __init__(self, diverge: bool = False):
        self.diverge = diverge

    def filter_part_iterations(self, part_master) -> list:
        """取最新修订版的最后 iteration（checked-in）。"""
        revisions = part_master.revisions or []
        if not revisions:
            return []
        last_rev = revisions[-1]
        last_it = last_rev.last_iteration
        return [last_it] if last_it else []

    def filter_links(self, path: list) -> list:
        """取路径最后一个 link；若 diverge 则追加替代链接。"""
        if not path:
            return []
        nominal = path[-1]
        result = [nominal]
        if self.diverge and getattr(nominal, 'substitutes', None):
            for sub in nominal.substitutes:
                result.append(sub)
        return result
