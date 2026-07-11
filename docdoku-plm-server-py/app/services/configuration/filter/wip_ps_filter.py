"""WIPPSFilter——工作中迭代过滤器。"""
from app.models.configuration.product_structure_filter import ProductStructureFilter


class WIPPSFilter(ProductStructureFilter):
    """选择最新可访问的 iteration（无论是否 checked-in）。

    对齐 Java WIPPSFilter。

    user_login: 当前用户登录名，用于权限检查。
    """

    def __init__(self, user_login: str, diverge: bool = False):
        self.user_login = user_login
        self.diverge = diverge

    def filter_part_iterations(self, part_master) -> list:
        """从最新 revision 向前找第一个用户可访问的 iteration。

        简化实现：返回最新 revision 的最后 iteration。
        Java 版本有更复杂的权限检查，Python 侧暂简化为取最新。
        """
        revisions = part_master.revisions or []
        for rev in reversed(revisions):
            last_it = rev.last_iteration
            if last_it:
                return [last_it]
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
