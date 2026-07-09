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
    EntityNotFoundException, PartUsageLinkNotFoundException,
)
from app.services.factory.acl_factory import apply_acl


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
                                  config_spec=None, path=None, depth=None,
                                  user_login: str = None, is_admin: bool = False):
        """返回递归 ComponentDTO 列表。每节点含 24 字段 + components[] 递归。

        若提供 config_spec（ProductStructureFilter 或 ProductConfigSpec），
        则使用 PSFilterVisitor 按配置规格遍历；否则走旧版全量遍历。
        """
        ci = self.get_ci(db, ws, ci_id)
        root_pn = ci.partmaster_partnumber
        master = db.query(PartMaster).filter(
            PartMaster.workspace_id == ws, PartMaster.number == root_pn).first()
        if master is None or not master.revisions:
            return []

        if config_spec is not None:
            return self._filter_with_visitor(db, master, config_spec, depth,
                                               ci_id, user_login, is_admin)

        root_rev = master.last_revision
        return [self._build_component(db, root_rev, None, ci_id, depth=depth,
                                       user_login=user_login, is_admin=is_admin)]

    def _filter_with_visitor(self, db: Session, root_pm, config_spec,
                              depth, ci_id, user_login, is_admin):
        """使用 PSFilterVisitor 遍历产品结构。"""
        from app.services.configuration import PSFilterVisitor

        visitor = PSFilterVisitor(db, root_pm.workspace_id, config_spec,
                                   stop_at_depth=depth)
        root_component = visitor.visit_from_master(root_pm)
        return [self._convert_visitor_component(db, root_component, ci_id,
                                                  user_login, is_admin)]

    def _convert_visitor_component(self, db: Session, comp, ci_id,
                                     user_login, is_admin):
        """将 PSFilterVisitor 返回的 Component 转为递归 dict。"""
        retained = comp.retained_iteration
        pm = comp.part_master
        rev = None
        if retained:
            rev = retained.revision

        result = {
            "number": pm.number,
            "name": pm.name or "",
            "version": rev.version if rev else (pm.last_revision.version if pm.revisions else "A"),
            "iteration": retained.iteration if retained else 0,
            "path": ci_id,
            "amount": 1.0,
            "unit": None,
            "optional": False,
            "partUsageLinkId": "u1",
            "description": rev.description if rev else "",
            "standardPart": pm.standard_part or False,
            "assembly": bool(retained and retained.components) if retained else False,
            "released": rev.status == 1 if rev else False,
            "obsolete": rev.status == 2 if rev else False,
            "author": pm.author_login or "",
            "authorLogin": pm.author_login or "",
            "checkOutUser": None,
            "checkOutDate": None,
            "lastIterationNumber": rev.last_iteration_number if rev else 0,
            "virtual": False,
            "substitute": False,
            "partUsageLinkReferenceDescription": None,
            "hasPathData": False,
            "accessDeny": False,
            "attributes": self._instance_attributes(
                db, pm.workspace_id, pm.number, rev.version,
                retained.iteration) if (rev and retained) else [],
            "components": [],
            "substituteIds": [],
            "notifications": self._modification_notifications(db, pm.workspace_id, pm.number),
        }
        for child in comp.components:
            child_dict = self._convert_visitor_component(db, child, ci_id,
                                                           user_login, is_admin)
            result["components"].append(child_dict)
        return result

    def _build_component(self, db: Session, rev: PartRevision, usage_link, path: str,
                          depth=None, user_login: str = None, is_admin: bool = False):
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
            sub_rows = db.execute(text(
                "SELECT DISTINCT psl.substitute_partnumber "
                "FROM partusagelink pul "
                "JOIN partsubstitutelink psl ON pul.id = psl.id "
                "WHERE pul.component_workspace_id = :ws "
                "AND pul.component_partnumber = :pn"
            ), {"ws": rev.workspace_id, "pn": rev.partmaster_partnumber}).fetchall()
            sub_ids = [r[0] for r in sub_rows]
        # accessDeny: 检查零件 ACL 权限
        access_deny = False
        if user_login and rev.acl_id:
            from app.services.factory.acl_factory import check_read_access
            access_deny = not check_read_access(db, rev.acl_id, user_login, is_admin)
        # notifications: 查询影响该零件主记录的修改通知
        notifications = self._modification_notifications(
            db, rev.workspace_id, rev.partmaster_partnumber)
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
            "hasPathData": self._check_has_path_data(db, rev.workspace_id, path),
            "accessDeny": access_deny,
            "attributes": self._instance_attributes(
                db, rev.workspace_id, rev.partmaster_partnumber, rev.version,
                last_it.iteration if last_it else None),
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
                                                     child_path, depth=child_depth,
                                                     user_login=user_login,
                                                     is_admin=is_admin)
                comp["components"].append(child_comp)
        return comp

    def _check_has_path_data(self, db: Session, ws: str, comp_path: str) -> bool:
        """检查组件路径是否有 PathDataMaster 记录。"""
        relative = comp_path.split("-", 1)[1] if "-" in comp_path else ""
        if not relative:
            return False
        row = db.execute(text(
            "SELECT 1 FROM pathdatamaster WHERE path = :p LIMIT 1"
        ), {"p": relative}).first()
        return row is not None

    # dtype(JPA 判别符) → InstanceAttributeType 枚举名（对齐 Payara InstanceAttributeDTO.type）
    _DTYPE_TO_TYPE = {
        "InstanceTextAttribute": "TEXT",
        "InstanceNumberAttribute": "NUMBER",
        "InstanceDateAttribute": "DATE",
        "InstanceBooleanAttribute": "BOOLEAN",
        "InstanceURLAttribute": "URL",
        "InstanceListOfValuesAttribute": "LOV",
        "InstanceLongTextAttribute": "LONG_TEXT",
        "InstancePartNumberAttribute": "PART_NUMBER",
    }

    def _instance_attributes(self, db: Session, ws: str, pn: str, ver: str, it: int) -> list:
        """查询零件迭代的实例属性，映射为 Payara InstanceAttributeDTO 形状。"""
        if it is None:
            return []
        rows = db.execute(text(
            "SELECT ia.dtype, ia.name, ia.mandatory, ia.locked, "
            "ia.textvalue, ia.numbervalue, ia.datevalue, ia.booleanvalue, "
            "ia.urlvalue, ia.longtextvalue "
            "FROM instanceattribute ia "
            "JOIN partiteration_attribute pia ON pia.instanceattribute_id = ia.id "
            "WHERE pia.workspace_id=:ws AND pia.partmaster_partnumber=:pn "
            "AND pia.partrevision_version=:ver AND pia.iteration=:it "
            "ORDER BY pia.attribute_order"
        ), {"ws": ws, "pn": pn, "ver": ver, "it": it}).fetchall()
        result = []
        for r in rows:
            dtype = r[0] or "InstanceTextAttribute"
            attr_type = self._DTYPE_TO_TYPE.get(dtype, "TEXT")
            # 按类型取值 → string（对齐 Java InstanceAttributeDTO.value:String）
            if attr_type in ("TEXT", "PART_NUMBER"):
                value = r[4]
            elif attr_type == "NUMBER":
                value = str(r[5]) if r[5] is not None else None
            elif attr_type == "DATE":
                value = str(r[6]) if r[6] is not None else None
            elif attr_type == "BOOLEAN":
                value = str(r[7]) if r[7] is not None else None
            elif attr_type == "URL":
                value = r[8]
            elif attr_type == "LONG_TEXT":
                value = r[9]
            else:
                value = r[4]
            result.append({
                "workspaceId": ws,
                "name": r[1] or "",
                "mandatory": r[2] or False,
                "locked": r[3] or False,
                "type": attr_type,
                "value": value if value is not None else "",
                "lovName": None,
                "items": [],
            })
        return result

    def _has_modification_notification(self, db: Session, ws: str, pn: str) -> bool:
        """零件主记录是否有修改通知（对齐 Java hasModificationNotification）。"""
        row = db.execute(text(
            "SELECT 1 FROM modificationnotification "
            "WHERE impacted_workspace_id = :ws AND impacted_partmaster_partnumber = :pn LIMIT 1"
        ), {"ws": ws, "pn": pn}).first()
        return row is not None

    def _modification_notifications(self, db: Session, ws: str, pn: str) -> list:
        """查询影响该零件主记录的修改通知列表。"""
        notif_rows = db.execute(text(
            "SELECT id, acknowledged, ackauthor_login, acknowledgementcomment, "
            "acknowledgementdate, ackauthor_workspace_id "
            "FROM modificationnotification WHERE impacted_workspace_id = :ws "
            "AND impacted_partmaster_partnumber = :pn"
        ), {"ws": ws, "pn": pn}).fetchall()
        return [
            {"id": r[0], "acknowledged": r[1], "ackAuthorLogin": r[2],
             "ackComment": r[3], "ackDate": str(r[4]) if r[4] else None,
             "ackAuthorWorkspaceId": r[5]}
            for r in notif_rows
        ]

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
                raise PartUsageLinkNotFoundException("PartUsageLinkNotFoundException", str(link_id))
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
