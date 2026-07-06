"""EffectivityConfigSpec 抽象基类。

按有效性规则过滤 PartRevision。所有有效性配置规格的基类。
对齐 Java EffectivityConfigSpec。
"""
from app.models.configuration.product_config_spec import ProductConfigSpec


class EffectivityConfigSpec(ProductConfigSpec):
    """有效性配置规格抽象基类。

    子类必须实现 is_effective(effectivity) 方法。

    configuration_item: ConfigurationItem（配置项）
    configuration: ProductConfiguration（可选，产品配置）
    """

    def __init__(self, configuration_item=None, configuration=None):
        super().__init__()
        self.configuration_item = configuration_item
        self.configuration = configuration

    def filter_part_iteration(self, part_master):
        """从最新 revision 向前找第一个满足有效性的 revision。"""
        revisions = part_master.revisions or []
        pr = None
        for i in range(len(revisions) - 1, -1, -1):
            if self._is_effective_revision(revisions[i]):
                pr = revisions[i]
                break

        if pr is not None:
            last_it = pr.last_iteration
            if last_it:
                self.retained_part_iterations.add(last_it)
                return last_it
        return None

    def filter_part_link(self, path: list) -> object:
        """过滤零件链接路径（处理可选件和替代件）。"""
        if not path:
            return None

        nominal = path[-1]

        if self.configuration is not None:
            # 有配置时：处理可选链接和替代链接
            if getattr(nominal, 'optional', False):
                path_str = self._path_as_string(path)
                if not self._is_optional_link_retained(path_str):
                    return None
                self.retained_optional_usage_links.add(path_str)

            # 检查替代链接
            for sub in getattr(nominal, 'substitutes', []) or []:
                sub_path = list(path)
                sub_path[-1] = sub
                sub_path_str = self._path_as_string(sub_path)
                if self._is_substitute_link_retained(sub_path_str):
                    self.retained_substitute_links.add(sub_path_str)
                    return sub

            return nominal
        else:
            return self._filter_nominal_link(path)

    def _filter_nominal_link(self, path: list):
        """无配置时：过滤可选链接。"""
        nominal = path[-1]
        if getattr(nominal, 'optional', False):
            return None
        return nominal

    def _is_effective_revision(self, pr) -> bool:
        """遍历 revision 的所有 Effectivity，只要有一个满足即返回 True。"""
        effectivities = getattr(pr, 'effectivities', []) or []
        for eff in effectivities:
            if self.is_effective(eff):
                return True
        return False

    def is_effective(self, effectivity) -> bool:
        """子类实现：判断指定 Effectivity 是否满足条件。"""
        raise NotImplementedError

    # ── 辅助方法（对齐 Java Tools.getPathAsString） ──

    @staticmethod
    def _path_as_string(path: list) -> str:
        """将路径转为字符串（如 "linkId1-linkId2"）。"""
        return "-".join(str(link.id) for link in path if hasattr(link, 'id'))

    def _is_optional_link_retained(self, path_str: str) -> bool:
        """检查可选链接是否被配置保留。默认不保留。"""
        return False

    def _is_substitute_link_retained(self, path_str: str) -> bool:
        """检查替代链接是否被配置保留。默认不保留。"""
        return False
