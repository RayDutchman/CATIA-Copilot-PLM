"""LatestReleasedPSFilter——最新已发布迭代过滤器。"""
from app.models.configuration.product_structure_filter import ProductStructureFilter


class LatestReleasedPSFilter(ProductStructureFilter):
    """取最新已发布修订版的最后 iteration。

    对齐 Java LatestReleasedPSFilter。严格单结果。
    """

    def __init__(self, diverge: bool = False):
        self.diverge = diverge

    def filter_part_iterations(self, part_master) -> list:
        """从后向前找第一个 status=1（RELEASED）的修订版，返回其最后迭代。"""
        revisions = part_master.revisions or []
        for rev in reversed(revisions):
            if rev.status == 1:  # RELEASED
                last_it = rev.last_iteration
                return [last_it] if last_it else []
        return []

    def filter_links(self, path: list) -> list:
        if not path:
            return []
        nominal = path[-1]
        result = [nominal]
        if self.diverge and getattr(nominal, 'substitutes', None):
            for sub in nominal.substitutes:
                result.append(sub)
        return result
