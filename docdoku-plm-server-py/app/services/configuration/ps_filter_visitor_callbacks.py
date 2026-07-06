"""PSFilterVisitorCallbacks 接口。

产品结构遍历回调。对齐 Java PSFilterVisitorCallbacks。
"""
from typing import List


class PSFilterVisitorCallbacks:
    """遍历回调——全部提供默认空实现，调用方可按需重写。"""

    def on_indeterminate_version(self, part_master, part_iterations: list) -> None:
        """filter 返回多个 iteration 时触发。"""

    def on_unresolved_version(self, part_master) -> None:
        """filter 返回0个 iteration 时触发。"""

    def on_indeterminate_path(self, current_path: list, part_iterations: list) -> None:
        """filter 返回多个合法路径时触发。"""

    def on_unresolved_path(self, current_path: list, part_iterations: list) -> None:
        """filter 返回0个路径且非 optional 时触发。"""

    def on_branch_discovered(self, current_path: list, part_iterations: list) -> None:
        """到达叶子节点（无子组件）时触发。"""

    def on_optional_path(self, path: list, part_iterations: list) -> None:
        """唯一匹配为 optional 时触发。"""

    def on_path_walk(self, path: list, parts: list) -> bool:
        """每步遍历前调用，返回 False 可中止该分支。"""
        return True
