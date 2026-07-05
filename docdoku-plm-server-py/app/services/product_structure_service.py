"""产品结构服务：ConfigurationItem CRUD + ComponentDTO 递归 + decodePath。"""
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models.product import (
    ConfigurationItem, ProductBaseline, ProductConfiguration,
    ProductInstanceMaster, ProductInstanceIteration,
)
from app.models.part import PartMaster, PartRevision, PartIteration, PartUsageLink, CADInstance
from app.core.exceptions import EntityAlreadyExistsException, EntityConstraintException


class ProductStructureService:

    def create_ci(self, db: Session, ws: str, ci_id: str, description: str,
                  part_number: str, user_login: str) -> ConfigurationItem:
        existing = db.query(ConfigurationItem).filter(
            ConfigurationItem.workspace_id == ws,
            ConfigurationItem.id == ci_id,
        ).first()
        if existing:
            raise EntityAlreadyExistsException(
                "ConfigurationItemAlreadyExistsException", ci_id)
        # 验证根零件存在（对齐 Java partMasterDAO.loadPartM）
        master = db.query(PartMaster).filter(
            PartMaster.workspace_id == ws,
            PartMaster.number == part_number,
        ).first()
        if master is None:
            raise HTTPException(404, f"未找到零件\"{part_number}\"")
        ci = ConfigurationItem(
            workspace_id=ws, id=ci_id, description=description,
            partmaster_workspace_id=ws, partmaster_partnumber=part_number,
            author_workspace_id=ws, author_login=user_login)
        db.add(ci); db.commit(); db.refresh(ci)
        return ci

    def list_cis(self, db: Session, ws: str):
        return db.query(ConfigurationItem).filter(
            ConfigurationItem.workspace_id == ws).all()

    def get_ci(self, db: Session, ws: str, ci_id: str):
        ci = db.query(ConfigurationItem).filter(
            ConfigurationItem.workspace_id == ws,
            ConfigurationItem.id == ci_id).first()
        if ci is None:
            raise HTTPException(404, "Configuration item not found")
        return ci

    def delete_ci(self, db: Session, ws: str, ci_id: str):
        ci = self.get_ci(db, ws, ci_id)
        # TODO(对齐审计): EntityConstraintException4(有基线)/13(有实例)/23(有配置)
        db.delete(ci); db.commit()

    def filter_product_structure(self, db: Session, ws: str, ci_id: str,
                                  config_spec=None, path=None, depth=None):
        """返回递归 ComponentDTO 列表。每节点含 24 字段 + components[] 递归。"""
        ci = self.get_ci(db, ws, ci_id)
        root_pn = ci.partmaster_partnumber
        master = db.query(PartMaster).filter(
            PartMaster.workspace_id == ws, PartMaster.number == root_pn).first()
        if master is None or not master.revisions:
            return []
        root_rev = master.last_revision
        return [self._build_component(db, root_rev, None, ci_id, depth=depth)]

    def _build_component(self, db: Session, rev: PartRevision, usage_link, path: str,
                         depth=None):
        last_it = rev.last_iteration
        comp = {
            "number": rev.partmaster_partnumber,
            "name": rev.part_master.name or "",
            "version": rev.version,
            "iteration": last_it.iteration if last_it else 0,
            "path": path,
            "amount": usage_link.amount if usage_link and usage_link.amount else 1.0,
            "unit": usage_link.unit if usage_link else None,
            "optional": usage_link.optional if usage_link else False,
            "partUsageLinkId": f"u{usage_link.id}" if usage_link else "u1",
            "description": rev.description or "",
            "standardPart": rev.part_master.standard_part or False,
            "assembly": bool(last_it and last_it.components),
            "released": rev.status == 1,
            "obsolete": rev.status == 2,
            "author": rev.author_login or "",
            "authorLogin": rev.author_login or "",
            "checkOutUser": {"login": rev.checkout_user_login} if rev.checkout_user_login else None,
            "checkOutDate": str(rev.check_out_date) if rev.check_out_date else None,
            "lastIterationNumber": rev.last_iteration_number,
            "virtual": False,
            "substitute": False,
            "partUsageLinkReferenceDescription": usage_link.reference_description if usage_link else None,
            "hasPathData": False,
            "accessDeny": False,
            "attributes": [],
            "components": [],
            "substituteIds": [],
            "notifications": [],
        }
        if last_it and (depth is None or depth > 0):
            child_depth = depth - 1 if depth is not None else None
            for order_link in (last_it.components or []):
                child_part = db.query(PartRevision).filter(
                    PartRevision.workspace_id == order_link.component_workspace_id,
                    PartRevision.partmaster_partnumber == order_link.component_partnumber,
                ).order_by(PartRevision.version.desc()).first()
                if child_part is None:
                    continue
                child_path = f"{path}-u{order_link.id}"
                child_comp = self._build_component(db, child_part, order_link,
                                                    child_path, depth=child_depth)
                comp["components"].append(child_comp)
        return comp

    def decode_path(self, db: Session, ws: str, ci_id: str, path_str: str):
        """u1-u4-u7 → [{id, partNumber, version, amount}]"""
        ci = self.get_ci(db, ws, ci_id)
        root_pn = ci.partmaster_partnumber
        master = db.query(PartMaster).filter(
            PartMaster.workspace_id == ws, PartMaster.number == root_pn).first()
        if master is None:
            return []
        segments = path_str.split("-")
        result = []
        for seg in segments:
            if not seg or seg[0] not in "us":
                continue
            link_id = int(seg[1:])
            link = db.query(PartUsageLink).filter(
                PartUsageLink.id == link_id).first()
            if link is None:
                break
            result.append({
                "id": link.id,
                "partNumber": link.component_partnumber,
                "version": "A",
                "amount": link.amount or 1.0,
                "unit": link.unit,
                "optional": link.optional or False,
            })
        return result

    def search_numbers(self, db: Session, ws: str, q: str):
        return db.query(ConfigurationItem).filter(
            ConfigurationItem.workspace_id == ws,
            ConfigurationItem.id.ilike(f"%{q}%"),
        ).all()

    # ── Baseline ──

    def list_baselines(self, db: Session, ws: str, ci_id=None):
        q = db.query(ProductBaseline).filter(
            ProductBaseline.configurationitem_workspace_id == ws)
        if ci_id:
            q = q.filter(ProductBaseline.configurationitem_id == ci_id)
        return q.all()

    def create_baseline(self, db: Session, ws: str, ci_id: str, name: str,
                        desc: str, bl_type: int, user_login: str):
        ci = self.get_ci(db, ws, ci_id)
        bl = ProductBaseline(
            name=name, description=desc, type=bl_type or 0,
            configurationitem_workspace_id=ws,
            configurationitem_id=ci_id,
            author_workspace_id=ws, author_login=user_login,
            creation_date=datetime.utcnow())
        db.add(bl); db.commit(); db.refresh(bl)
        return bl

    def delete_baseline(self, db: Session, ws: str, bl_id: int):
        bl = db.query(ProductBaseline).filter(
            ProductBaseline.id == bl_id).first()
        if bl is None:
            raise HTTPException(404, "Baseline not found")
        db.delete(bl); db.commit()

    # ── Configuration ──

    def create_config(self, db: Session, ws: str, ci_id: str, name: str,
                       desc: str, user_login: str):
        ci = self.get_ci(db, ws, ci_id)
        cfg = ProductConfiguration(
            name=name, description=desc,
            configurationitem_workspace_id=ws,
            configurationitem_id=ci_id,
            author_workspace_id=ws, author_login=user_login,
            creation_date=datetime.utcnow())
        db.add(cfg); db.commit(); db.refresh(cfg)
        return cfg

    def list_configs(self, db: Session, ws: str, ci_id=None):
        q = db.query(ProductConfiguration).filter(
            ProductConfiguration.configurationitem_workspace_id == ws)
        if ci_id:
            q = q.filter(ProductConfiguration.configurationitem_id == ci_id)
        return q.all()

    def delete_config(self, db: Session, ws: str, cfg_id: int):
        cfg = db.query(ProductConfiguration).filter(
            ProductConfiguration.id == cfg_id).first()
        if cfg is None:
            raise HTTPException(404, "Configuration not found")
        db.delete(cfg); db.commit()

    # ── Instance ──

    def create_instance(self, db: Session, ws: str, ci_id: str, serial: str,
                        baseline_id: int, user_login: str):
        existing = db.query(ProductInstanceMaster).filter(
            ProductInstanceMaster.workspace_id == ws,
            ProductInstanceMaster.serialnumber == serial,
        ).first()
        if existing:
            raise EntityAlreadyExistsException(
                "ProductInstanceAlreadyExistsException", serial)
        master = ProductInstanceMaster(
            serialnumber=serial, workspace_id=ws,
            configurationitem_id=ci_id)
        db.add(master); db.flush()
        db.add(ProductInstanceIteration(
            workspace_id=ws, configurationitem_id=ci_id,
            prdinstancemaster_serialnumber=serial, iteration=1,
            productbaseline_id=baseline_id,
            author_workspace_id=ws, author_login=user_login,
            creation_date=datetime.utcnow()))
        db.commit(); db.refresh(master)
        return master

    def list_instances(self, db: Session, ws: str, ci_id=None):
        q = db.query(ProductInstanceMaster).filter(
            ProductInstanceMaster.workspace_id == ws)
        if ci_id:
            q = q.filter(ProductInstanceMaster.configurationitem_id == ci_id)
        return q.all()

    def delete_instance(self, db: Session, ws: str, ci_id: str, serial: str):
        inst = db.query(ProductInstanceMaster).filter(
            ProductInstanceMaster.workspace_id == ws,
            ProductInstanceMaster.configurationitem_id == ci_id,
            ProductInstanceMaster.serialnumber == serial).first()
        if inst is None:
            raise HTTPException(404, "Instance not found")
        db.execute(text("DELETE FROM productinstanceiteration WHERE "
            "workspace_id=:ws AND configurationitem_id=:ci AND "
            "prdinstancemaster_serialnumber=:sn"),
            {"ws": ws, "ci": ci_id, "sn": serial})
        db.delete(inst); db.commit()
