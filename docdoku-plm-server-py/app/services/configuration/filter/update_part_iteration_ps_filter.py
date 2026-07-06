"""UpdatePartIterationPSFilter——更新迭代后的循环装配检测过滤器。"""
from app.models.configuration.product_structure_filter import ProductStructureFilter
from app.models.product.part_master import PartMaster
from app.models.product.part_iteration import PartIteration


class UpdatePartIterationPSFilter(ProductStructureFilter):
    """对根部件返回当前迭代；对其他部件返回 WIP + latest。

    对齐 Java UpdatePartIterationPSFilter（用于更新后的循环装配检测）。

    root_iteration: 正在更新的部件迭代。
    对其他部件：返回 checked-in 的最后迭代 和 WIP 的最后迭代（可能重复会去重）。
    """

    def __init__(self, root_iteration: PartIteration):
        self.root_iteration = root_iteration
        root_rev = root_iteration.revision
        root_pm = root_rev.part_master
        self.root_key = (root_pm.workspace_id, root_pm.number)

    def filter_part_iterations(self, part_master) -> list:
        """根部件返回当前迭代；其他部件返回 checked-in + WIP 的所有迭代。"""
        pm_key = (part_master.workspace_id, part_master.number)
        if pm_key == self.root_key:
            return [self.root_iteration]

        # 对其他部件：返回所有 revision 的最后迭代（WIP + checked-in）
        revisions = part_master.revisions or []
        result = []
        seen = set()
        for rev in revisions:
            last_it = rev.last_iteration
            if last_it:
                key = (last_it.workspace_id, last_it.partmaster_partnumber,
                       last_it.partrevision_version, last_it.iteration)
                if key not in seen:
                    seen.add(key)
                    result.append(last_it)
        return result

    def filter_links(self, path: list) -> list:
        """始终分叉（diverge=true）：包含所有替代链接。"""
        if not path:
            return []
        nominal = path[-1]
        result = [nominal]
        if hasattr(nominal, 'substitutes') and nominal.substitutes:
            for sub in nominal.substitutes:
                result.append(sub)
        return result
