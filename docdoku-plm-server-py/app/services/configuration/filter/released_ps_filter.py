"""ReleasedPSFilter——所有已发布迭代过滤器。"""
from app.models.configuration.product_structure_filter import ProductStructureFilter


class ReleasedPSFilter(ProductStructureFilter):
    """取所有已发布修订版的最后 iteration。

    对齐 Java ReleasedPSFilter。可能返回多个结果。
    """

    def __init__(self, diverge: bool = False):
        self.diverge = diverge

    def filter_part_iterations(self, part_master) -> list:
        """遍历所有 status=1 的修订版，取每个的最后迭代。"""
        revisions = part_master.revisions or []
        result = []
        for rev in revisions:
            if rev.status == 1:  # RELEASED
                last_it = rev.last_iteration
                if last_it:
                    result.append(last_it)
        return result

    def filter_links(self, path: list) -> list:
        if not path:
            return []
        nominal = path[-1]
        result = [nominal]
        if self.diverge and nominal.substitutes:
            for sub in nominal.substitutes:
                result.append(sub)
        return result
