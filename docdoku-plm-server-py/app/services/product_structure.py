"""产品结构服务：ConfigurationItem CRUD + ComponentDTO 递归 + decodePath。"""
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models.product import (
    ConfigurationItem, ProductBaseline, ProductConfiguration,
    ProductInstanceMaster, ProductInstanceIteration,
)
from app.models.part import PartMaster, PartRevision, PartUsageLink
from app.models.auth import Account
from app.models.notification import ModificationNotification
from app.core.exceptions import (
    EntityAlreadyExistsException, EntityConstraintException,
    EntityNotFoundException,
)
from app.services.acl_helper import apply_acl


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
            raise EntityNotFoundException("PartMasterNotFoundException", part_number)
        ci = ConfigurationItem(
            workspace_id=ws, id=ci_id, description=description,
            creation_date=datetime.utcnow(),
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
            raise EntityNotFoundException("ConfigurationItemNotFoundException", ci_id)
        return ci

    def delete_ci(self, db: Session, ws: str, ci_id: str):
        ci = self.get_ci(db, ws, ci_id)
        bl_count = db.execute(text(
            "SELECT COUNT(*) FROM productbaseline "
            "WHERE configurationitem_id=:ci AND configurationitem_workspace_id=:ws"
        ), {"ci": ci_id, "ws": ws}).scalar()
        if bl_count:
            raise EntityConstraintException("EntityConstraintException4")
        cfg_count = db.execute(text(
            "SELECT COUNT(*) FROM productconfiguration "
            "WHERE configurationitem_id=:ci"
        ), {"ci": ci_id}).scalar()
        if cfg_count:
            raise EntityConstraintException("EntityConstraintException23")
        inst_count = db.execute(text(
            "SELECT COUNT(*) FROM productinstancemaster "
            "WHERE configurationitem_id=:ci"
        ), {"ci": ci_id}).scalar()
        if inst_count:
            raise EntityConstraintException("EntityConstraintException13")
        db.delete(ci); db.commit()

    def update_ci(self, db: Session, ws: str, ci_id: str, body: dict) -> ConfigurationItem:
        ci = self.get_ci(db, ws, ci_id)
        if "description" in body:
            ci.description = body["description"]
        design_item = body.get("designItemNumber") or body.get("partNumber") or body.get("partMasterNumber")
        if design_item:
            master = db.query(PartMaster).filter(
                PartMaster.workspace_id == ws,
                PartMaster.number == design_item,
            ).first()
            if master is None:
                raise EntityNotFoundException("PartMasterNotFoundException", design_item)
            ci.partmaster_partnumber = design_item
            ci.partmaster_workspace_id = ws
        db.commit()
        db.refresh(ci)
        return ci

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
        # author: 对齐 Java ComponentDTO.setAuthor(pm.getAuthor().getName())
        author_name = rev.part_master.author_login or ""
        pm_author_acct = db.query(Account).filter(
            Account.login == rev.part_master.author_login).first()
        if pm_author_acct and pm_author_acct.name:
            author_name = pm_author_acct.name
        # checkOutUser: 对齐 Java UserDTO（含 login/name/email/workspaceId）
        chk_user = None
        if rev.checkout_user_login:
            chk_user = {
                "login": rev.checkout_user_login,
                "workspaceId": rev.checkout_user_workspace_id,
            }
            chk_acct = db.query(Account).filter(
                Account.login == rev.checkout_user_login).first()
            if chk_acct:
                chk_user["name"] = chk_acct.name
                chk_user["email"] = chk_acct.email
                chk_user["language"] = chk_acct.language
        # virtual/substitute: 对齐 Java usageLink instanceof PartSubstituteLink
        is_virtual = False
        is_substitute = False
        if usage_link:
            is_virtual = getattr(usage_link, 'is_virtual', False)
            is_substitute = getattr(usage_link, 'is_substitute', False)
        # substituteIds: 查询该零件的替件
        sub_ids = []
        if last_it:
            sub_ids = []  # PartUsageLink.getSubstitutes() 需通过 usage_link 关联查询
        # notifications: 查询影响该零件主记录的修改通知
        notif_rows = db.execute(text(
            "SELECT id, acknowledged, ackauthor_login, acknowledgementcomment, "
            "acknowledgementdate, ackauthor_workspace_id "
            "FROM modificationnotification WHERE impacted_workspace_id = :ws "
            "AND impacted_partmaster_partnumber = :pn"
        ), {"ws": rev.workspace_id, "pn": rev.partmaster_partnumber}).fetchall()
        notifications = [
            {"id": r[0], "acknowledged": r[1], "ackAuthorLogin": r[2],
             "ackComment": r[3], "ackDate": str(r[4]) if r[4] else None,
             "ackAuthorWorkspaceId": r[5]}
            for r in notif_rows
        ]
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
            "author": author_name,
            "authorLogin": rev.part_master.author_login or "",
            "checkOutUser": chk_user,
            "checkOutDate": str(rev.check_out_date) if rev.check_out_date else None,
            "lastIterationNumber": rev.last_iteration_number,
            "virtual": is_virtual,
            "substitute": is_substitute,
            "partUsageLinkReferenceDescription": usage_link.reference_description if usage_link else None,
            "hasPathData": False,
            "accessDeny": False,
            "attributes": [],
            "components": [],
            "substituteIds": sub_ids,
            "notifications": notifications,
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
        """u1-u4-u7 → LightPartLinkDTO[{number, name, referenceDescription, fullId}]"""
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
            rev = db.query(PartRevision).filter(
                PartRevision.workspace_id == ws,
                PartRevision.partmaster_partnumber == link.component_partnumber,
            ).order_by(PartRevision.version.desc()).first()
            pn = link.component_partnumber
            ver = rev.version if rev else "A"
            result.append({
                "number": pn,
                "name": rev.part_master.name if rev and rev.part_master.name else pn,
                "referenceDescription": link.reference_description if link.reference_description else "",
                "fullId": f"{ws}/{pn}/{ver}",
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
                        desc: str, bl_type: int, user_login: str,
                        baselined_parts: list | None = None,
                        substitute_links: list | None = None,
                        optional_usage_links: list | None = None):
        ci = self.get_ci(db, ws, ci_id)
        # 创建 PartCollection
        db.execute(text(
            "INSERT INTO partcollection (creationdate, author_workspace_id, author_login) "
            "VALUES (now(), :ws, :login)"), {"ws": ws, "login": user_login})
        db.flush()
        pc_id = db.execute(text("SELECT currval('partcollection_id_seq')")).scalar()
        bl = ProductBaseline(
            name=name, description=desc, type=bl_type or 0,
            configurationitem_workspace_id=ws,
            configurationitem_id=ci_id,
            author_workspace_id=ws, author_login=user_login,
            partcollection_id=pc_id,
            creation_date=datetime.utcnow())
        db.add(bl); db.flush()
        if baselined_parts:
            for bp in baselined_parts:
                db.execute(text(
                    "INSERT INTO baselinedpart "
                    "(target_workspace_id, target_partmaster_partnumber, "
                    "target_partrevision_version, target_iteration, partcollection_id) "
                    "VALUES (:ws, :pn, :ver, :iter, :pcid)"
                ), {"ws": ws, "pn": bp.get("partNumber", ""),
                    "ver": bp.get("version", "A"), "iter": bp.get("iteration", 1),
                    "pcid": pc_id})
        if substitute_links:
            for sl in substitute_links:
                db.execute(text(
                    "INSERT INTO partsubstitutelink "
                    "(component_workspace_id, component_partnumber, "
                    "substitute_workspace_id, substitute_partnumber) "
                    "VALUES (:cws, :cpn, :sws, :spn)"
                ), {"cws": ws, "cpn": sl.get("partNumber", ""),
                    "sws": ws, "spn": sl.get("substitutePartNumber", "")})
        if optional_usage_links:
            for ol in optional_usage_links:
                db.execute(text(
                    "UPDATE partusagelink SET optional = true "
                    "WHERE component_workspace_id = :ws "
                    "AND component_partnumber = :pn "
                    "AND component_partversion = :ver"
                ), {"ws": ws, "pn": ol.get("partNumber", ""),
                    "ver": ol.get("version", "A")})
        db.commit(); db.refresh(bl)
        return bl

    def delete_baseline(self, db: Session, ws: str, bl_id: int):
        bl = db.query(ProductBaseline).filter(
            ProductBaseline.id == bl_id).first()
        if bl is None:
            raise EntityNotFoundException("BaselineNotFoundException", str(bl_id))
        db.delete(bl); db.commit()

    # ── Configuration ──

    def create_config(self, db: Session, ws: str, ci_id: str, name: str,
                       desc: str, user_login: str,
                       substitute_links: list | None = None,
                       optional_usage_links: list | None = None,
                       acl_user_entries: dict | None = None,
                       acl_group_entries: dict | None = None):
        ci = self.get_ci(db, ws, ci_id)
        acl_id = None
        if acl_user_entries or acl_group_entries:
            acl_id = apply_acl(db, None, acl_user_entries or {}, acl_group_entries or {})
        cfg = ProductConfiguration(
            name=name, description=desc,
            configurationitem_workspace_id=ws,
            configurationitem_id=ci_id,
            author_workspace_id=ws, author_login=user_login,
            acl_id=acl_id,
            creation_date=datetime.utcnow())
        db.add(cfg); db.flush()
        if substitute_links:
            for sl in substitute_links:
                db.execute(text(
                    "INSERT INTO partsubstitutelink "
                    "(component_workspace_id, component_partnumber, "
                    "substitute_workspace_id, substitute_partnumber) "
                    "VALUES (:cws, :cpn, :sws, :spn)"
                ), {"cws": ws, "cpn": sl.get("partNumber", ""),
                    "sws": ws, "spn": sl.get("substitutePartNumber", "")})
        if optional_usage_links:
            for ol in optional_usage_links:
                db.execute(text(
                    "UPDATE partusagelink SET optional = true "
                    "WHERE component_workspace_id = :ws "
                    "AND component_partnumber = :pn "
                    "AND component_partversion = :ver"
                ), {"ws": ws, "pn": ol.get("partNumber", ""),
                    "ver": ol.get("version", "A")})
        db.commit(); db.refresh(cfg)
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
            raise EntityNotFoundException("ProductConfigurationNotFoundException", str(cfg_id))
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
            raise EntityNotFoundException("ProductInstanceMasterNotFoundException", serial)
        db.execute(text("DELETE FROM productinstanceiteration WHERE "
            "workspace_id=:ws AND configurationitem_id=:ci AND "
            "prdinstancemaster_serialnumber=:sn"),
            {"ws": ws, "ci": ci_id, "sn": serial})
        db.delete(inst); db.commit()
