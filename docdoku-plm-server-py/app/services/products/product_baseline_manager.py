"""ProductBaselineManager——产品基线与配置管理。

对齐 Java ProductBaselineManagerBean。
底层 delegate 到 ProductStructureService（已有基线/配置 CRUD），
本服务增加 PSFilterVisitor 驱动的高级创建流程。
"""
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.part import PartMaster


class ProductBaselineService:
    """产品基线与配置管理服务。"""

    def __init__(self):
        from app.services.product_structure import ProductStructureService
        self._product = ProductStructureService()

    def create_baseline(self, db: Session, ws: str, ci_id: str,
                         name: str, baseline_type: int, description: str = "",
                         effective_date: datetime = None,
                         effective_serial: str = None,
                         effective_lot: str = None,
                         baselined_parts: list = None,
                         substitute_links: list = None,
                         optional_usage_links: list = None,
                         user_login: str = "",
                         dry_run: bool = False) -> dict:
        """创建产品基线。

        支持基于日期/序列号/批次号的有效性过滤基线，或直接指定部件列表创建基线。
        """
        if effective_date is not None:
            return self._create_effectivity_baseline(
                db, ws, ci_id, name, description, baseline_type,
                effective_date=effective_date, user_login=user_login,
                dry_run=dry_run)
        elif effective_serial is not None:
            return self._create_effectivity_baseline(
                db, ws, ci_id, name, description, baseline_type,
                effective_serial=effective_serial, user_login=user_login,
                dry_run=dry_run)
        elif effective_lot is not None:
            return self._create_effectivity_baseline(
                db, ws, ci_id, name, description, baseline_type,
                effective_lot=effective_lot, user_login=user_login,
                dry_run=dry_run)

        # 直接指定部件列表的基线创建
        bl = self._product.create_baseline(
            db, ws, ci_id, name, description, baseline_type, user_login,
            baselined_parts=baselined_parts,
            substitute_links=substitute_links,
            optional_usage_links=optional_usage_links)
        return self._to_dict(bl)

    def _create_effectivity_baseline(self, db, ws, ci_id, name, desc,
                                       bl_type, **kwargs):
        """基于有效性过滤创建基线（使用 PSFilterVisitor 遍历产品结构）。"""
        from app.services.configuration import (
            PSFilterVisitor, PSFilterVisitorCallbacks,
            DateBasedEffectivityConfigSpec,
            SerialNumberBasedEffectivityConfigSpec,
            LotBasedEffectivityConfigSpec,
        )
        ci = self._product.get_ci(db, ws, ci_id)
        root_pn = ci.partmaster_partnumber
        pm = db.query(PartMaster).filter(
            PartMaster.workspace_id == ws, PartMaster.number == root_pn).first()
        if not pm:
            raise Exception("Root PartMaster not found")

        # 选择配置规格
        if kwargs.get("effective_date"):
            spec = DateBasedEffectivityConfigSpec(kwargs["effective_date"], ci)
        elif kwargs.get("effective_serial"):
            spec = SerialNumberBasedEffectivityConfigSpec(kwargs["effective_serial"], ci)
        elif kwargs.get("effective_lot"):
            spec = LotBasedEffectivityConfigSpec(kwargs["effective_lot"], ci)
        else:
            raise ValueError("No effectivity parameter specified")

        # 遍历
        class BaselineCallbacks(PSFilterVisitorCallbacks):
            def __init__(self):
                self.visited_paths = set()
            def on_path_walk(self, path, parts):
                self.visited_paths.add(tuple(str(getattr(l, 'id', '')) for l in path))
                return True

        callbacks = BaselineCallbacks()
        visitor = PSFilterVisitor(db, ws, spec, callbacks)
        visitor.visit_from_master(pm)

        # 收集部件迭代
        baselined_parts = []
        for pi in spec.retained_part_iterations:
            baselined_parts.append({
                "partNumber": pi.partmaster_partnumber,
                "version": pi.partrevision_version,
                "iteration": pi.iteration,
            })

        return self.create_baseline(
            db, ws, ci_id, name, bl_type, desc,
            baselined_parts=baselined_parts,
            user_login=kwargs.get("user_login", ""),
            dry_run=kwargs.get("dry_run", False))

    def get_all_baselines(self, db: Session, ws: str) -> list:
        return [self._to_dict(b) for b in self._product.list_baselines(db, ws)]

    def get_baselines_by_ci(self, db: Session, ws: str, ci_id: str) -> list:
        return [self._to_dict(b) for b in self._product.list_baselines(db, ws, ci_id=ci_id)]

    def get_baseline(self, db: Session, ws: str, baseline_id: int) -> dict:
        from sqlalchemy import text
        bl = db.execute(text(
            "SELECT * FROM productbaseline WHERE id=:id AND configurationitem_workspace_id=:ws"
        ), {"id": baseline_id, "ws": ws}).first()
        if not bl:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("BaselineNotFoundException", str(baseline_id))
        return {"id": bl[0], "name": bl[1], "description": bl[2], "type": bl[3] if len(bl) > 3 else 0}

    def delete_baseline(self, db: Session, ws: str, baseline_id: int):
        return self._product.delete_baseline(db, ws, baseline_id)

    def create_configuration(self, db: Session, ws: str, ci_id: str, name: str,
                              description: str = "", user_login: str = "",
                              substitute_links: list = None,
                              optional_usage_links: list = None,
                              acl_user_entries: dict = None,
                              acl_group_entries: dict = None) -> dict:
        cfg = self._product.create_config(
            db, ws, ci_id, name, description, user_login,
            substitute_links=substitute_links,
            optional_usage_links=optional_usage_links,
            acl_user_entries=acl_user_entries,
            acl_group_entries=acl_group_entries)
        return self._cfg_to_dict(cfg)

    def list_configurations(self, db: Session, ws: str, ci_id: str = None) -> list:
        return [self._cfg_to_dict(c) for c in self._product.list_configs(db, ws, ci_id)]

    def get_configuration(self, db: Session, ws: str, ci_id: str, cfg_id: int) -> dict:
        from sqlalchemy import text
        cfg = db.execute(text(
            "SELECT * FROM productconfiguration WHERE id=:id AND configurationitem_id=:ci"
        ), {"id": cfg_id, "ci": ci_id}).first()
        if not cfg:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("ProductConfigurationNotFoundException", str(cfg_id))
        return {"id": cfg[0], "name": cfg[1], "description": cfg[2] if len(cfg) > 2 else ""}

    def delete_configuration(self, db: Session, ws: str, cfg_id: int):
        return self._product.delete_config(db, ws, cfg_id)

    def _to_dict(self, bl) -> dict:
        return {"id": bl.id, "name": bl.name, "description": bl.description,
                "type": getattr(bl, 'type', 0), "creationDate": str(getattr(bl, 'creation_date', ''))}

    def _cfg_to_dict(self, cfg) -> dict:
        return {"id": cfg.id, "name": cfg.name, "description": cfg.description}


product_baseline_service = ProductBaselineService()
