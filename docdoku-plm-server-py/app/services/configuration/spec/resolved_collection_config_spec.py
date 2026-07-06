"""ResolvedCollectionConfigSpec——基于已解析集合的配置规格。"""
from app.models.configuration.product_config_spec import ProductConfigSpec


class ResolvedCollectionConfigSpec(ProductConfigSpec):
    """从 ResolvedCollection（PartCollection + 替代件/可选件）中取配置。

    对齐 Java ResolvedCollectionConfigSpec。
    """

    def __init__(self, part_collection, resolved_collection):
        super().__init__()
        self.part_collection = part_collection
        self.resolved_collection = resolved_collection
        self._optional_usage_links = set()
        self._substitute_usage_links = set()

    def filter_part_iteration(self, part_master):
        """从 PartCollection 中查找基线化零件并返回目标迭代。"""
        # 简化实现：PartCollection 关联 BaselinedPart 列表
        baselined_parts = getattr(self.part_collection, 'baselined_parts', []) or []
        pm_kp = (part_master.workspace_id, part_master.number)
        for bp in baselined_parts:
            bp_kp = (getattr(bp, 'workspace_id', None), getattr(bp, 'partmaster_number', None))
            if bp_kp == pm_kp:
                # 从 revision 中取对应迭代
                target_ver = getattr(bp, 'target_version', None)
                target_iter = getattr(bp, 'target_iteration', None)
                revisions = part_master.revisions or []
                for rev in revisions:
                    if rev.version == target_ver:
                        for it in (rev.iterations or []):
                            if it.iteration == target_iter:
                                self.retained_part_iterations.add(it)
                                return it
        return None

    def filter_part_link(self, path: list):
        """过滤可选链接和替代链接。"""
        if not path:
            return None
        nominal = path[-1]

        # 处理可选链接：仅在 retained 集合中的保留
        path_str = self._path_as_string(path)
        path_str_list = self._path_as_list(path)
        if getattr(nominal, 'optional', False):
            # 简化：检查路径是否被保留
            return nominal

        # 处理替代链接：检查替代件是否在指定集合中
        for sub in getattr(nominal, 'substitutes', []) or []:
            sub_path = list(path)
            sub_path[-1] = sub
            sub_path_str = self._path_as_string(sub_path)
            if sub_path_str in self._substitute_usage_links:
                self.retained_substitute_links.add(sub_path_str)
                return sub

        return nominal

    @staticmethod
    def _path_as_string(path: list) -> str:
        return "-".join(str(link.id) for link in path if hasattr(link, 'id'))

    @staticmethod
    def _path_as_list(path: list) -> list:
        return [link.id for link in path if hasattr(link, 'id')]
