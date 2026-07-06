"""ProductBaselineCreationConfigSpec——基线创建时的配置规格。"""
from app.models.configuration.product_config_spec import ProductConfigSpec
from app.models.configuration.product_baseline_type import ProductBaselineType


class ProductBaselineCreationConfigSpec(ProductConfigSpec):
    """创建基线时使用的配置规格。

    对齐 Java ProductBaselineCreationConfigSpec。
    """

    def __init__(self, baseline_type: ProductBaselineType,
                 part_iterations: list,
                 substitute_links: list,
                 optional_usage_links: list):
        super().__init__()
        self.baseline_type = baseline_type
        self._part_iterations = part_iterations
        self._substitute_links = set(substitute_links or [])
        self._optional_usage_links = set(optional_usage_links or [])

    def filter_part_iteration(self, part_master):
        """根据基线类型和指定的迭代列表返回对应迭代。"""
        for pi in self._part_iterations:
            if (pi.workspace_id == part_master.workspace_id and
                pi.partmaster_partnumber == part_master.number):
                return pi
        return None

    def filter_part_link(self, path: list):
        """从基线指定路径筛选链接。"""
        if not path:
            return None
        return path[-1]
