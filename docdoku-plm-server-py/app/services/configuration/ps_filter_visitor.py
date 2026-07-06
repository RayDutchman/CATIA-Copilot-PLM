"""PSFilterVisitor——产品结构遍历引擎。

用 ProductStructureFilter 和 PSFilterVisitorCallbacks 递归遍历零件树。
对齐 Java PSFilterVisitor。

关键机制：
  - 版本分支展开：filter 返回多个 PartIteration 时，各自展开子组件
  - 循环引用检测：路径上已出现过的 PartMaster 再次出现则抛异常
  - stop() 中断：防止后续递归继续展开
  - 深度控制：stop_at_depth 限制遍历深度
"""
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.configuration.product_structure_filter import ProductStructureFilter
from app.models.product.part_master import PartMaster
from app.models.product.part_revision import PartRevision
from app.models.product.part_iteration import PartIteration
from app.models.product.part_usage_link import PartUsageLink
from app.models.product.part_substitute_link import PartSubstituteLink
from app.core.exceptions import EntityConstraintException


class Component:
    """递归结构树节点（简化 Component DTO）。"""

    def __init__(self, author_name: str = "", part_master=None,
                 path: list = None, retained_iteration=None):
        self.author_name = author_name
        self.part_master = part_master
        self.path = path or []
        self.retained_iteration = retained_iteration
        self.components: List["Component"] = []

    def set_components(self, children: list):
        self.components = children


class PSFilterVisitor:
    """产品结构遍历引擎。

    用法:
        visitor = PSFilterVisitor(db, workspace_id, psfilter, callbacks)
        root = visitor.visit_from_master(root_part_master)
        # 或
        root = visitor.visit_from_path(root_part_master, existing_path)
    """

    _ROOT_FULL_ID = "-1"

    def __init__(self, db: Session, workspace_id: str,
                 psfilter: ProductStructureFilter,
                 callbacks: "PSFilterVisitorCallbacks" = None,
                 stop_at_depth: int = None):
        self.db = db
        self.workspace_id = workspace_id
        self.filter = psfilter
        self.callbacks = callbacks or _DefaultCallbacks()
        self.stop_at_depth = stop_at_depth if stop_at_depth is not None else -1
        self.stopped = False

    def stop(self):
        """中断遍历。"""
        self.stopped = True

    def visit_from_master(self, part_master: PartMaster) -> Component:
        """从 PartMaster 出发遍历。

        PartMaster 必须有 __iter__ 等可迭代方法。"""
        return self._visit(
            part_master,
            [self._create_virtual_root_link(part_master)],
            [part_master],
        )

    def visit_from_path(self, part_master: PartMaster, starting_path: list) -> Component:
        """从已有路径出发遍历。"""
        return self._visit(part_master, starting_path, [part_master])

    # ── 私有方法 ──────────────────────────────────────

    def _visit(self, pm: PartMaster, starting_path: list,
               current_path_parts: list) -> Component:
        """创建根 Component 并启动递归。"""
        author_name = getattr(pm, 'author_login', "") or ""
        component = Component(author_name=author_name, part_master=pm,
                              path=starting_path)
        children = self._get_components_recursively(
            component, [], current_path_parts, starting_path)
        component.set_components(children)
        return component

    def _get_components_recursively(self, current_component: Component,
                                     current_path_iterations: list,
                                     current_path_parts: list,
                                     current_path: list) -> List[Component]:
        """核心递归方法。"""
        components = []

        if self.stopped:
            return components

        # 路径进入回调
        if not self.callbacks.on_path_walk(list(current_path), list(current_path_parts)):
            return components

        current_pm = current_path_parts[-1]

        # 过滤版本
        part_iterations = self.filter.filter_part_iterations(current_pm)

        if not part_iterations:
            self.callbacks.on_unresolved_version(current_pm)

        if len(part_iterations) > 1:
            self.callbacks.on_indeterminate_version(current_pm, list(part_iterations))

        if len(part_iterations) == 1:
            current_component.retained_iteration = part_iterations[0]

        # 遍历每个迭代（可能 >1，实现分支展开）
        for part_iteration in part_iterations:
            copy_part_iterations = list(current_path_iterations)
            copy_part_iterations.append(part_iteration)

            # 叶子节点
            comps = getattr(part_iteration, 'components', []) or []
            if not comps:
                self.callbacks.on_branch_discovered(
                    list(current_path), list(copy_part_iterations))
                continue

            # 遍历子链接
            for usage_link in comps:
                child_path = list(current_path)
                child_path.append(usage_link)

                # 过滤链接
                eligible_links = self.filter.filter_links(child_path)

                if not eligible_links and not getattr(usage_link, 'optional', False):
                    self.callbacks.on_unresolved_path(
                        list(child_path), list(copy_part_iterations))

                if len(eligible_links) > 1:
                    self.callbacks.on_indeterminate_path(
                        list(child_path), list(copy_part_iterations))

                if len(eligible_links) == 1 and getattr(eligible_links[0], 'optional', False):
                    self.callbacks.on_optional_path(
                        list(child_path), list(copy_part_iterations))

                # 遍历过滤后的每条合法链接
                for link in eligible_links:
                    next_path = list(current_path)
                    next_path.append(link)

                    # 深度控制
                    current_depth = len(current_path_parts)
                    if self.stop_at_depth != -1 and self.stop_at_depth < current_depth:
                        continue

                    # 加载子 PartMaster
                    child_pm = self._load_part_master(link)

                    # 循环引用检测
                    if child_pm in current_path_parts:
                        raise EntityConstraintException("EntityConstraintException12",
                            f"Circular reference detected: {child_pm.number}")

                    copy_path_parts = list(current_path_parts)
                    copy_path_parts.append(child_pm)
                    copy_path = list(next_path)

                    sub = Component(
                        author_name=getattr(child_pm, 'author_login', "") or "",
                        part_master=child_pm,
                        path=copy_path,
                    )
                    sub.set_components(
                        self._get_components_recursively(
                            sub, list(copy_part_iterations), copy_path_parts, copy_path))
                    components.append(sub)

        return components

    def _load_part_master(self, link) -> PartMaster:
        """通过链接加载子 PartMaster（对齐 Java partMasterDAO.loadPartM）。"""
        from app.models.product.part_usage_link import PartUsageLink
        from app.models.product.part_substitute_link import PartSubstituteLink

        if isinstance(link, PartUsageLink):
            ws = link.component_workspace_id
            pn = link.component_partnumber
        elif isinstance(link, PartSubstituteLink):
            ws = link.substitute_workspace_id
            pn = link.substitute_partnumber
        else:
            # 虚拟根链接
            return link.get_component() if hasattr(link, 'get_component') else None

        pm = self.db.query(PartMaster).filter(
            PartMaster.workspace_id == ws,
            PartMaster.number == pn,
        ).first()
        if pm is None:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("PartMasterNotFoundException", pn)
        return pm

    @staticmethod
    def _create_virtual_root_link(part_master: PartMaster):
        """创建虚拟根链接（对齐 Java createVirtualRootLink）。"""
        class VirtualRootLink:
            id = 1
            amount = 1.0
            unit = None
            comment = ""
            optional = False
            reference_description = None
            substitutes = []
            full_id = "-1"
            code = '-'

            @staticmethod
            def get_component():
                return part_master

        return VirtualRootLink()


class _DefaultCallbacks:
    """默认空回调实现。"""

    def on_indeterminate_version(self, *args): pass
    def on_unresolved_version(self, *args): pass
    def on_indeterminate_path(self, *args): pass
    def on_unresolved_path(self, *args): pass
    def on_branch_discovered(self, *args): pass
    def on_optional_path(self, *args): pass
    def on_path_walk(self, *args): return True
