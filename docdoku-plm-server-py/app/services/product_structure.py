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
    EntityNotFoundException, PartMasterNotFoundException,
    PartUsageLinkNotFoundException,
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

    @staticmethod
    def parse_config_spec_str(config_spec_str: str, db: Session = None,
                               user_login: str = None):
        """将 configSpec 字符串解析为 ProductStructureFilter 或 ProductConfigSpec 对象。

        对齐 Payara ProductManagerBean.getConfigSpec(configSpecType, workspaceId)：
        - "latest"        → LatestCheckedInPSFilter
        - "released"      → LatestReleasedPSFilter
        - "wip"           → WIPPSFilter
        - "pi-{serial}"   → 产品实例 configSpec（暂用 wip fallback）
        - 整数字符串      → 基线 ID → ResolvedCollectionConfigSpec（需 DB 查询）
        若无法识别则返回 None（全量遍历）。
        """
        if not config_spec_str:
            return None
        val = config_spec_str.strip().lower()
        if val == "latest":
            from app.services.configuration.filter.latest_checked_in_ps_filter import LatestCheckedInPSFilter
            return LatestCheckedInPSFilter()
        if val == "released":
            from app.services.configuration.filter.latest_released_ps_filter import LatestReleasedPSFilter
            return LatestReleasedPSFilter()
        if val == "wip":
            from app.services.configuration.filter.wip_ps_filter import WIPPSFilter
            return WIPPSFilter(user_login=user_login or "")
        if val.startswith("pi-"):
            # 产品实例规格：暂用 wip fallback
            from app.services.configuration.filter.wip_ps_filter import WIPPSFilter
            return WIPPSFilter(user_login=user_login or "")
        # 尝试解析为基线 ID
        # 注意：PSFilterVisitor 需要 ProductStructureFilter（filter_part_iterations），
        # 而 ResolvedCollectionConfigSpec 继承 ProductConfigSpec（filter_part_iteration 单数），
        # 两者接口不匹配，不能直接传给 PSFilterVisitor。
        # 基线 configSpec 暂用全量遍历（return None），
        # 待实现 ProductBaselinePSFilter（继承 ProductStructureFilter）后再接入。
        try:
            int(config_spec_str)  # 验证是合法整数
            # 基线 ID configSpec：降级为全量遍历（不过滤），避免接口不匹配导致 500
            return None
        except (ValueError, TypeError):
            pass
        return None

    def filter_product_structure(self, db: Session, ws: str, ci_id: str,
                                  config_spec=None, path=None, depth=None,
                                  user_login: str = None, is_admin: bool = False):
        """返回递归 ComponentDTO 列表。每节点含 24 字段 + components[] 递归。

        若提供 config_spec（字符串或 ProductStructureFilter/ProductConfigSpec 对象），
        则解析后使用 PSFilterVisitor 按配置规格遍历；否则走旧版全量遍历。
        """
        # 若传入的是字符串，先解析为 filter 对象
        if isinstance(config_spec, str):
            config_spec = self.parse_config_spec_str(config_spec, db=db, user_login=user_login)

        ci = self.get_ci(db, ws, ci_id)
        root_pn = ci.partmaster_partnumber
        master = db.query(PartMaster).filter(
            PartMaster.workspace_id == ws, PartMaster.number == root_pn).first()
        if master is None:
            raise PartMasterNotFoundException("PartMasterNotFoundException", root_pn)
        if not master.revisions:
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
                                     user_login, is_admin, parent_path=None):
        """将 PSFilterVisitor 返回的 Component 转为递归 dict。

        comp.path 是 PSFilterVisitor 构建的 PartUsageLink 列表（根节点为空列表）。
        path 格式对齐 Java：根="ceshi"，子="ceshi-u4262"，孙="ceshi-u4262-u4271"。
        partUsageLinkId 格式："u{link_id}"（根节点为 "u1"）。
        """
        retained = comp.retained_iteration
        pm = comp.part_master
        rev = None
        if retained:
            rev = retained.revision

        # 从 PSFilterVisitor 的 path 列表构建路径字符串
        # VirtualRootLink（full_id="-1"）需跳过，对齐 Java createVirtualRootLink
        if comp.path and getattr(comp.path[-1], 'full_id', None) != '-1':
            usage_link = comp.path[-1]
            path_str = f"{parent_path}-u{usage_link.id}" if parent_path else f"{ci_id}-u{usage_link.id}"
            part_usage_link_id = f"u{usage_link.id}"
        else:
            path_str = parent_path if parent_path else ci_id
            part_usage_link_id = "-1"

        # virtual/substitute: 从 path 末位 link 判断
        is_virtual = False
        is_substitute = False
        if comp.path:
            usage_link = comp.path[-1]
            is_virtual = getattr(usage_link, 'is_virtual', False)
            is_substitute = getattr(usage_link, 'is_substitute', False)

        result = {
            "number": pm.number,
            "name": pm.name or "",
            "version": rev.version if rev else (pm.last_revision.version if pm.revisions else "A"),
            "iteration": retained.iteration if retained else 0,
            "path": path_str,
            "amount": float(comp.path[-1].amount) if comp.path and hasattr(comp.path[-1], 'amount') and comp.path[-1].amount else 1.0,
            "unit": comp.path[-1].unit if comp.path else None,
            "optional": bool(comp.path[-1].optional) if comp.path else False,
            "partUsageLinkId": part_usage_link_id,
            "description": rev.description if rev else "",
            "standardPart": pm.standard_part or False,
            "assembly": bool(retained and retained.components) if retained else False,
            "released": rev.status == 1 if rev else False,
            "obsolete": rev.status == 2 if rev else False,
            "author": self._resolve_user_name(db, pm.author_login),
            "authorLogin": pm.author_login or "",
            "checkOutUser": None,
            "checkOutDate": None,
            "lastIterationNumber": rev.last_iteration_number if rev else 0,
            "virtual": is_virtual,
            "substitute": is_substitute,
            "partUsageLinkReferenceDescription": (comp.path[-1].reference_description
                                                   if comp.path else None),
            "hasPathData": self._check_has_path_data_from_link_path(
                db, comp.path, comp.part_master.workspace_id if comp.part_master else ""
            ),
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
                                                           user_login, is_admin,
                                                           parent_path=path_str)
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

    def _check_has_path_data_from_link_path(self, db: Session,
                                              link_path: list, ws: str) -> bool:
        """从 PartLink 列表路径检查是否有 PathDataMaster 记录。

        link_path 是 PSFilterVisitor Component.path（PartLink 对象列表）。
        构建 "-1-u{id1}-u{id2}" 格式的路径字符串再查 DB。
        """
        if not link_path:
            return False
        parts = []
        for link in link_path:
            link_id = getattr(link, 'id', None)
            if link_id is None:
                return False
            # PartUsageLink → "u", PartSubstituteLink → "s"
            from app.models.part import PartSubstituteLink
            prefix = "s" if isinstance(link, PartSubstituteLink) else "u"
            parts.append(f"{prefix}{link_id}")
        db_path = "-1-" + "-".join(parts)
        row = db.execute(text(
            "SELECT 1 FROM pathdatamaster WHERE path = :p LIMIT 1"
        ), {"p": db_path}).first()
        return row is not None

    def _resolve_user_name(self, db: Session, login: str) -> str:
        """查 Account 表返回用户真实姓名，找不到时降级为 login。"""
        if not login:
            return ""
        acc = db.query(Account).filter(Account.login == login).first()
        if acc and acc.name:
            return acc.name
        return login

    def _check_has_path_data(self, db: Session, ws: str, comp_path: str) -> bool:
        """检查组件路径是否有 PathDataMaster 记录。

        comp_path 格式：{ci_id}-u2-u5（如 "BIKE-u2-u5"）。
        pathdatamaster.path 存储的是 "-1-u2-u5"（Java 格式，以 -1 为根节点）。
        需要将 {ci_id} 前缀替换为 -1 再查询。
        """
        if not comp_path or "-u" not in comp_path and "-s" not in comp_path:
            return False
        # 取第一个 - 后的部分（"-u2-u5"），拼上 "-1" 前缀
        dash_idx = comp_path.find("-")
        if dash_idx == -1:
            return False
        suffix = comp_path[dash_idx:]  # 形如 "-u2-u5"
        db_path = "-1" + suffix       # 形如 "-1-u2-u5"
        row = db.execute(text(
            "SELECT 1 FROM pathdatamaster WHERE path = :p LIMIT 1"
        ), {"p": db_path}).first()
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
            raise PartMasterNotFoundException("PartMasterNotFoundException", root_pn)
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

        # 零件可用性校验（对齐 Java ProductBaselineCreationConfigSpec + PSFilterVisitor）
        root_pn = ci.partmaster_partnumber
        master = db.query(PartMaster).filter(
            PartMaster.workspace_id == ws, PartMaster.number == root_pn).first()
        if master:
            self._validate_baseline_parts(db, master, bl_type)

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

    def _validate_baseline_parts(self, db: Session, root_pm, bl_type: int):
        """BFS 遍历产品结构，校验所有零件有可用迭代。

        对齐 Java ProductBaselineCreationConfigSpec + PSFilterVisitor：
        - LATEST(0)：每个零件必须有最后已签入迭代（lastCheckedInIteration）
        - RELEASED(1)：每个零件必须至少有一个发布版本
        不满足 → NotAllowedException49（零件号不含可用迭代）
        """
        from app.core.exceptions import NotAllowedException
        visited = set()
        queue = [root_pm]

        while queue:
            pm = queue.pop(0)
            key = (pm.workspace_id, pm.number)
            if key in visited:
                continue
            visited.add(key)

            if bl_type == 0:  # LATEST — 对齐 Java getLastCheckedInIteration()
                rev = pm.last_revision
                if rev is None:
                    raise NotAllowedException("NotAllowedException49", pm.number)
                # 已签出的零件无可用迭代（Java: checkOutUser != null → null）
                if rev.checkout_user_login:
                    raise NotAllowedException("NotAllowedException49", pm.number)
                last_it = rev.last_iteration
                if last_it is None:
                    raise NotAllowedException("NotAllowedException49", pm.number)
                for link in (last_it.components or []):
                    child = db.query(PartMaster).filter(
                        PartMaster.workspace_id == link.component_workspace_id,
                        PartMaster.number == link.component_partnumber,
                    ).first()
                    if child:
                        queue.append(child)
            else:  # RELEASED (1) 或其他
                has_released = db.execute(text(
                    "SELECT 1 FROM partrevision "
                    "WHERE workspace_id = :ws AND partmaster_partnumber = :pn "
                    "AND status = 1 LIMIT 1"
                ), {"ws": pm.workspace_id, "pn": pm.number}).first()
                if not has_released:
                    raise NotAllowedException("NotAllowedException49", pm.number)
                # 通过已发布版本遍历子件
                released_rev = db.query(PartRevision).filter(
                    PartRevision.workspace_id == pm.workspace_id,
                    PartRevision.partmaster_partnumber == pm.number,
                    PartRevision.status == 1,
                ).order_by(PartRevision.version.desc()).first()
                if released_rev:
                    last_it = released_rev.last_iteration
                    if last_it:
                        for link in (last_it.components or []):
                            child = db.query(PartMaster).filter(
                                PartMaster.workspace_id == link.component_workspace_id,
                                PartMaster.number == link.component_partnumber,
                            ).first()
                            if child:
                                queue.append(child)


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
