"""产品结构服务：ConfigurationItem CRUD + ComponentDTO 递归 + decodePath。"""
import re
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

    # ── UserDTO 辅助（内联版，避免跨文件依赖）──

    @staticmethod
    def _build_user_dto(db: Session, login: str, ws: str) -> dict:
        if not login:
            return {"login": "", "name": "", "email": None, "language": None, "workspaceId": ws}
        acc = db.query(Account).filter(Account.login == login).first()
        name = acc.name if (acc and acc.name) else login
        return {"login": login, "name": name, "email": None, "language": None, "workspaceId": ws}

    # ── CI DTO ──

    def build_ci_dto(self, db: Session, ci: ConfigurationItem) -> dict:
        """构建 ConfigurationItemDTO dict（对齐 Java）。"""
        from app.services.products.path_to_path_service import path_to_path_service
        from app.models.util.date_utils import format_iso_date
        name = ""
        latest_version = ""
        if ci.partmaster_partnumber:
            master = db.query(PartMaster).filter(
                PartMaster.workspace_id == ci.workspace_id,
                PartMaster.number == ci.partmaster_partnumber,
            ).first()
            if master:
                name = master.name or ""
            rev = db.query(PartRevision).filter(
                PartRevision.workspace_id == ci.workspace_id,
                PartRevision.partmaster_partnumber == ci.partmaster_partnumber,
            ).order_by(PartRevision.creation_date.desc()).first()
            if rev:
                latest_version = rev.version
        try:
            p2p_links = path_to_path_service.get_links_for_ci(db, ci.workspace_id, ci.id)
        except Exception:
            p2p_links = []
        return {
            "id": ci.id, "workspaceId": ci.workspace_id,
            "description": ci.description,
            "designItemNumber": ci.partmaster_partnumber,
            "designItemName": name,
            "designItemLatestVersion": latest_version,
            "author": self._build_user_dto(db, ci.author_login, ci.workspace_id),
            "creationDate": format_iso_date(ci.creation_date),
            "hasModificationNotification": self._has_modification_notification(
                db, ci.workspace_id, ci.partmaster_partnumber
            ) if ci.partmaster_partnumber else False,
            "pathToPathLinks": p2p_links,
        }

    # ── Last Release ──

    def get_last_release_dto(self, db: Session, ws: str, ci_id: str) -> dict:
        """返回 CI 根零件的最新已发布版本 DTO。"""
        from app.models.util.date_utils import format_iso_date
        ci = self.get_ci(db, ws, ci_id)
        root_pn = ci.partmaster_partnumber
        rev = db.query(PartRevision).filter(
            PartRevision.workspace_id == ws,
            PartRevision.partmaster_partnumber == root_pn,
            PartRevision.status == 1,
        ).order_by(PartRevision.version.desc()).first()
        if rev is None:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("NoReleasedRevisionException", ci_id)
        last_it = rev.last_iteration
        author_name = rev.part_master.author_login or ""
        pm_author = db.query(Account).filter(Account.login == rev.part_master.author_login).first()
        if pm_author and pm_author.name:
            author_name = pm_author.name
        chk_user = None
        if rev.checkout_user_login:
            chk_acct = db.query(Account).filter(Account.login == rev.checkout_user_login).first()
            chk_user = {
                "login": rev.checkout_user_login,
                "name": (chk_acct.name if chk_acct and chk_acct.name else rev.checkout_user_login) or "",
                "email": chk_acct.email if chk_acct else None,
                "language": chk_acct.language if chk_acct else None,
                "workspaceId": rev.checkout_user_workspace_id or ws,
            }
        return {
            "partKey": f"{rev.partmaster_partnumber}-{rev.version}",
            "number": rev.partmaster_partnumber,
            "version": rev.version,
            "name": rev.part_master.name or "",
            "iteration": last_it.iteration if last_it else 1,
            "description": rev.description or "",
            "author": author_name,
            "authorLogin": rev.part_master.author_login or "",
            "checkOutUser": chk_user,
            "checkOutDate": format_iso_date(rev.check_out_date),
            "releaseDate": format_iso_date(rev.release_date),
            "standardPart": rev.part_master.standard_part or False,
            "assembly": bool(last_it and last_it.components),
            "workspaceId": ws,
            "configurationItemId": ci_id,
        }

    # ── Path/Versions Choices ──

    def get_path_choices(self, db: Session, ws: str, ci_id: str) -> list:
        """返回 CI 下已存在的路径数据列表。"""
        rows = db.execute(text(
            "SELECT DISTINCT pdm.path, pdm.id FROM pathdatamaster pdm "
            "JOIN prdinstiteration_pathdatamstr pipd ON pdm.id = pipd.pathdatamaster_id "
            "JOIN productinstanceiteration pii ON pii.workspace_id = pipd.workspace_id "
            "AND pii.configurationitem_id = pipd.configurationitem_id "
            "AND pii.prdinstancemaster_serialnumber = pipd.prdinstancemaster_serialnumber "
            "AND pii.iteration = pipd.prdinstanceiteration_iteration "
            "JOIN productinstancemaster pim ON pim.workspace_id = pii.workspace_id "
            "AND pim.configurationitem_id = pii.configurationitem_id "
            "AND pim.serialnumber = pii.prdinstancemaster_serialnumber "
            "WHERE pim.workspace_id = :ws AND pim.configurationitem_id = :ci"
        ), {"ws": ws, "ci": ci_id}).fetchall()
        return [{"id": r[1], "path": r[0]} for r in rows]

    def get_versions_choices(self, db: Session, ws: str, ci_id: str) -> list:
        """返回 CI 根零件的所有版本列表。"""
        ci = self.get_ci(db, ws, ci_id)
        root_pn = ci.partmaster_partnumber
        revs = db.query(PartRevision).filter(
            PartRevision.workspace_id == ws,
            PartRevision.partmaster_partnumber == root_pn,
        ).order_by(PartRevision.version).all()
        result = []
        for rev in revs:
            last_it = rev.last_iteration
            result.append({
                "partNumber": rev.partmaster_partnumber,
                "version": rev.version,
                "iteration": last_it.iteration if last_it else 1,
                "name": rev.part_master.name or "",
            })
        return result

    # ── CI Path Search ──

    def search_ci_paths(self, db: Session, ws: str, ci_id: str,
                         search: str = None, config_spec: str = None,
                         diverge: bool = False, user_login: str = None) -> list:
        """在装配结构中递归搜索路径（对齐 Java ProductResource.searchPaths）。"""
        import re
        ci = self.get_ci(db, ws, ci_id)
        root_master = (
            db.query(PartMaster)
            .filter(
                PartMaster.workspace_id == ws,
                PartMaster.number == ci.partmaster_partnumber,
            )
            .first()
        )
        if root_master is None:
            return []

        ps_filter = None
        if config_spec:
            ps_filter = self.parse_config_spec_str(config_spec, db=db, user_login=user_login, diverge=diverge)

        try:
            pattern = re.compile(search) if search else None
        except re.error:
            pattern = re.compile(re.escape(search)) if search else None

        collected: list[str] = []

        def walk(master, path_parts: list[str]):
            path_str = "-".join(path_parts)
            if pattern is None or (
                pattern.search(master.number or "")
                or pattern.search(master.name or "")
                or pattern.search(path_str)
            ):
                if path_str:
                    collected.append(path_str)

            if not master.revisions:
                return
            if ps_filter:
                filtered = ps_filter.filter_part_iterations(master)
                last_it = filtered[0] if filtered else None
            else:
                last_rev = master.revisions[-1]
                last_it = last_rev.iterations[-1] if last_rev and last_rev.iterations else None

            if not last_it:
                return
            for link in (last_it.components or []):
                child_master = (
                    db.query(PartMaster)
                    .filter(
                        PartMaster.workspace_id == ws,
                        PartMaster.number == link.component_partnumber,
                    )
                    .first()
                )
                if child_master:
                    child_path = path_parts + [str(link.id)]
                    walk(child_master, child_path)

        walk(root_master, [])
        return [{"path": p} for p in collected]

    # ── CI Document Links ──

    def get_ci_document_links(self, db: Session, ws: str, ci_id: str,
                               pn: str, pv: str, pi: int, config_spec: str) -> list:
        """获取零件迭代在指定基线中关联的文档（对齐 Java）。"""
        from app.models.configuration.product_baseline import ProductBaseline
        from app.models.configuration.baselined_document import BaselinedDocument
        from app.models.configuration.product_instance_iteration import ProductInstanceIteration
        from app.models.part import PartIteration
        from app.models.document.document_revision import DocumentRevision
        from app.models.document.document_link import DocumentLink

        baseline = None
        if config_spec.startswith("pi-"):
            serial_number = config_spec[3:]
            last_pii = db.query(ProductInstanceIteration).filter(
                ProductInstanceIteration.workspace_id == ws,
                ProductInstanceIteration.configurationitem_id == ci_id,
                ProductInstanceIteration.prdinstancemaster_serialnumber == serial_number,
            ).order_by(ProductInstanceIteration.iteration.desc()).first()
            if last_pii and last_pii.productbaseline_id:
                baseline = db.query(ProductBaseline).filter(
                    ProductBaseline.id == last_pii.productbaseline_id,
                ).first()
        else:
            try:
                bl_id = int(config_spec)
                baseline = db.query(ProductBaseline).filter(
                    ProductBaseline.id == bl_id,
                ).first()
            except ValueError:
                baseline = None

        if baseline is None:
            return []

        baselined_docs = db.query(BaselinedDocument).filter(
            BaselinedDocument.documentcollection_id == baseline.documentcollection_id,
        ).all() if baseline.documentcollection_id else []

        if not baselined_docs:
            return []

        pi_obj = db.query(PartIteration).filter(
            PartIteration.workspace_id == ws,
            PartIteration.partmaster_partnumber == pn,
            PartIteration.partrevision_version == pv,
            PartIteration.iteration == pi,
        ).first()

        if pi_obj is None:
            return []

        link_rows = db.execute(text("""
            SELECT documentlink_id FROM partiteration_documentlink
            WHERE workspace_id = :ws AND partmaster_partnumber = :pn
              AND partrevision_version = :pv AND iteration = :pi
        """), {"ws": ws, "pn": pn, "pv": pv, "pi": pi}).fetchall()

        if not link_rows:
            return []

        doc_links = db.query(DocumentLink).filter(
            DocumentLink.id.in_([r[0] for r in link_rows]),
        ).all() if link_rows else []

        result = []
        for bd in baselined_docs:
            target_rev = db.query(DocumentRevision).filter(
                DocumentRevision.workspace_id == bd.target_workspace_id,
                DocumentRevision.documentmaster_id == bd.target_documentmaster_id,
                DocumentRevision.version == bd.target_docrevision_version,
            ).first()
            if target_rev is None:
                continue

            for dl in doc_links:
                if (dl.target_workspace_id == bd.target_workspace_id
                        and dl.target_documentmaster_id == bd.target_documentmaster_id
                        and dl.target_docrevision_version == bd.target_docrevision_version):
                    result.append({
                        "documentMasterId": bd.target_documentmaster_id,
                        "version": bd.target_docrevision_version,
                        "title": target_rev.title or "",
                        "iteration": bd.target_iteration,
                        "workspaceId": bd.target_workspace_id,
                        "commentLink": dl.comment or "",
                    })

        return result

    def get_ci_document_links_wip(self, db: Session, ws: str, ci_id: str,
                                    pn: str, config_spec: str) -> list:
        """返回 CI 下指定零件的最新 document-links（WIP 配置规约）。"""
        from app.models.document.document_link import DocumentLink

        rev = db.query(PartRevision).filter(
            PartRevision.workspace_id == ws,
            PartRevision.partmaster_partnumber == pn,
        ).order_by(PartRevision.creation_date.desc()).first()
        if not rev:
            return []
        last_it = rev.last_iteration
        if not last_it:
            return []
        links = db.query(DocumentLink).filter(
            DocumentLink.workspace_id == ws,
            DocumentLink.partmaster_partnumber == last_it.partmaster_partnumber,
            DocumentLink.partrevision_version == last_it.partrevision_version,
            DocumentLink.iteration == last_it.iteration,
        ).all()
        result = []
        for dl in links:
            result.append({
                "documentMasterId": dl.targetdocumentmaster_id,
                "documentRevisionVersion": dl.targetdocumentrevision_version,
                "iteration": dl.target_iteration,
                "workspaceId": ws,
                "commentLink": dl.comment or "",
            })
        return result

    # ── BOM Flatten ──

    def flatten_bom_to_part_list(self, comp_list: list, ws: str, ci_id: str) -> list:
        """将 ComponentDTO 树平铺为 PartRevisionDTO 列表。"""
        parts = []

        def flatten(comp, level=0):
            parts.append({
                "partKey": f"{comp['number']}-{comp['version']}",
                "number": comp["number"],
                "version": comp["version"],
                "iteration": comp["iteration"],
                "name": comp["name"],
                "description": comp["description"],
                "checkOutUser": comp.get("checkOutUser"),
                "status": "RELEASED" if comp["released"] else ("OBSOLETE" if comp["obsolete"] else "WIP"),
                "author": comp["author"],
                "authorLogin": comp["authorLogin"],
                "checkOutDate": comp.get("checkOutDate"),
                "standardPart": comp["standardPart"],
                "assembly": comp["assembly"],
                "workspaceId": ws,
                "configurationItemId": ci_id,
                "notifications": comp.get("notifications", []),
            })
            for child in comp.get("components", []):
                flatten(child, level + 1)

        for comp in comp_list:
            flatten(comp)
        return parts

    # ── CRUD ──

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
                               user_login: str = None, diverge: bool = False,
                               ws: str = None, ci_id: str = None):
        """将 configSpec 字符串解析为 ProductStructureFilter 或 ProductConfigSpec 对象。

        对齐 Payara ProductManagerBean.getConfigSpec(configSpecType, workspaceId)：
        - "latest"        → LatestCheckedInPSFilter
        - "released"      → LatestReleasedPSFilter
        - "wip"           → WIPPSFilter
        - "pi-{serial}"   → 产品实例基线过滤（需 db+ws+ci_id，否则降级 WIP）
        - 整数字符串      → 基线 ID → ResolvedCollectionConfigSpec（需 DB 查询）
        若无法识别则返回 None（全量遍历）。
        """
        if not config_spec_str:
            return None
        val = config_spec_str.strip().lower()
        if val == "latest":
            from app.services.configuration.filter.latest_checked_in_ps_filter import LatestCheckedInPSFilter
            return LatestCheckedInPSFilter(diverge=diverge)
        if val == "released":
            from app.services.configuration.filter.latest_released_ps_filter import LatestReleasedPSFilter
            return LatestReleasedPSFilter(diverge=diverge)
        if val == "wip":
            from app.services.configuration.filter.wip_ps_filter import WIPPSFilter
            return WIPPSFilter(user_login=user_login or "", diverge=diverge)
        if val.startswith("pi-"):
            serial = config_spec_str.strip()[3:]
            # 优先级：有 db+ws+ci_id → 真实解析 baselinedpart 过滤
            if db and ws and ci_id:
                return ProductStructureService._resolve_pi_config_spec(
                    db, ws, ci_id, serial, user_login, diverge)
            # 无 DB 上下文时降级为 WIP（而非 latest，因 pi 实例语义更接近 WIP）
            from app.services.configuration.filter.wip_ps_filter import WIPPSFilter
            return WIPPSFilter(user_login=user_login or "", diverge=diverge)
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
                                   user_login: str = None, is_admin: bool = False,
                                   link_type: str | None = None,
                                   diverge: bool = False):
        """返回递归 ComponentDTO 列表。每节点含 24 字段 + components[] 递归。

        若提供 config_spec（字符串或 ProductStructureFilter/ProductConfigSpec 对象），
        则解析后使用 PSFilterVisitor 按配置规格遍历；否则走旧版全量遍历。
        link_type 非空时按 P2P linkType 过滤结构（P2-08）。
        """
        # P2-08: linkType 过滤分支
        if link_type is not None:
            return self._filter_on_link_type(db, ws, ci_id, config_spec, path,
                                              link_type, user_login, is_admin)

        # 若传入的是字符串，先解析为 filter 对象
        if isinstance(config_spec, str):
            config_spec = self.parse_config_spec_str(config_spec, db=db, user_login=user_login, diverge=diverge)

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

        comp_path 格式：{ci_id}-u2-u5（如 "BIKE-u2-u5" 或 "ACLCI-45ECFC-u2"）。
        pathdatamaster.path 存储的是 "-1-u2-u5"（Java 格式，以 -1 为根节点）。
        用正则定位首个 -u{id} 或 -s{id}（而非第一个 -），避免 CI ID 含连字符时定位错误。
        对齐 Java ProductResource.createComponentDTO() → getPathAsString 的路径格式。
        """
        if not comp_path or "-u" not in comp_path and "-s" not in comp_path:
            return False
        # 定位首个 -u{id} 或 -s{id}，而非第一个连字符（CI ID 可能含 -）
        m = re.search(r'-(?:u|s)\d+', comp_path)
        if not m:
            return False
        db_path = "-1" + comp_path[m.start():]
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
        """u1-u4-u7 → LightPartLinkDTO[{number, name, referenceDescription, fullId}]

        P2-09 已对齐 Java LightPartLinkDTO 四字段。
        """
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
                        optional_usage_links: list | None = None,
                        effective_date=None, effective_serial_number: str | None = None,
                        effective_lot_id: str | None = None):
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
        # effectivity(2/3/4) 的迭代选择已上移至 ProductBaselineService._create_effectivity_baseline
        # （config-spec + PSFilterVisitor 驱动），此处仅按传入的 baselined_parts 落库
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
        - EFFECTIVE_DATE/SERIAL/LOT(2/3/4)：跳过强校验（effectivity 数据可能缺失）
        不满足 → NotAllowedException49（零件号不含可用迭代）
        """
        from app.core.exceptions import NotAllowedException
        # EFFECTIVE 类型跳过强校验——effectivity 关联表数据可能缺失，退化 LATEST
        if bl_type in (2, 3, 4):
            return
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
        ref = db.execute(
            text("SELECT 1 FROM productinstanceiteration WHERE productbaseline_id = :bid"),
            {"bid": bl_id},
        ).first()
        if ref is not None:
            raise EntityConstraintException("EntityConstraintException16")
        pc_id = bl.partcollection_id
        dc_id = bl.documentcollection_id
        bid = bl.id
        db.execute(
            text("DELETE FROM baselinedpart WHERE partcollection_id = :pc_id"),
            {"pc_id": pc_id},
        )
        db.execute(
            text("DELETE FROM baselineddocument WHERE documentcollection_id = :dc_id"),
            {"dc_id": dc_id},
        )
        db.execute(
            text("DELETE FROM productbaseline_substitutelink WHERE productbaseline_id = :bid"),
            {"bid": bid},
        )
        db.execute(
            text("DELETE FROM productbaseline_optionallink WHERE productbaseline_id = :bid"),
            {"bid": bid},
        )
        db.execute(
            text("DELETE FROM productbaseline_p2plink WHERE productbaseline_id = :bid"),
            {"bid": bid},
        )
        # 先删 productbaseline 行（flush 立即执行），解除其对 partcollection/documentcollection
        # 的 FK 引用，否则后续删集合会违反 fk_productbaseline_partcollection_id（对齐 Payara 204）
        db.delete(bl)
        db.flush()
        if pc_id is not None:
            db.execute(
                text("DELETE FROM partcollection WHERE id = :pc_id"),
                {"pc_id": pc_id},
            )
        if dc_id is not None:
            db.execute(
                text("DELETE FROM documentcollection WHERE id = :dc_id"),
                {"dc_id": dc_id},
            )
        db.commit()

    # ── Configuration ──

    def get_config_substitute_paths(self, db: Session, config_id: int) -> list:
        rows = db.execute(text(
            "SELECT substitutelinks FROM prdcfg_substitutelink "
            "WHERE productbaseline_id = :cid"
        ), {"cid": config_id}).fetchall()
        return [r[0] for r in rows if r[0]]

    def get_config_optional_paths(self, db: Session, config_id: int) -> list:
        rows = db.execute(text(
            "SELECT optionalusagelinks FROM prdcfg_optionallink "
            "WHERE productbaseline_id = :cid"
        ), {"cid": config_id}).fetchall()
        return [r[0] for r in rows if r[0]]

    def get_config_by_id(self, db: Session, ws: str, ci_id: str, cfg_id: int) -> ProductConfiguration:
        cfg = db.query(ProductConfiguration).filter(
            ProductConfiguration.id == cfg_id,
            ProductConfiguration.configurationitem_id == ci_id,
            ProductConfiguration.configurationitem_workspace_id == ws,
        ).first()
        if not cfg:
            raise EntityNotFoundException("ProductConfigurationNotFoundException", str(cfg_id))
        return cfg

    def update_config_acl(self, db: Session, ws: str, ci_id: str, cfg_id: int,
                           user_entries: dict, group_entries: dict):
        config = self.get_config_by_id(db, ws, ci_id, cfg_id)
        if not user_entries and not group_entries:
            config.acl_id = None
            db.commit()
            return {"aclId": None}
        acl_id = getattr(config, "acl_id", None)
        new_acl_id = apply_acl(db, acl_id, user_entries, group_entries)
        if config.acl_id != new_acl_id:
            config.acl_id = new_acl_id
            db.commit()
        return {"aclId": new_acl_id}

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

        def _normalize_path(p) -> str | None:
            """将元素统一为路径字符串（兼容历史上可能的 dict 入参）"""
            if isinstance(p, str):
                return p
            if isinstance(p, dict):
                return p.get("fullPath") or p.get("path")
            return None

        if substitute_links:
            for sl in substitute_links:
                path = _normalize_path(sl)
                if path:
                    db.execute(text(
                        "INSERT INTO prdcfg_substitutelink "
                        "(productbaseline_id, substitutelinks) "
                        "VALUES (:cid, :path)"
                    ), {"cid": cfg.id, "path": path})
        if optional_usage_links:
            for ol in optional_usage_links:
                path = _normalize_path(ol)
                if path:
                    db.execute(text(
                        "INSERT INTO prdcfg_optionallink "
                        "(productbaseline_id, optionalusagelinks) "
                        "VALUES (:cid, :path)"
                    ), {"cid": cfg.id, "path": path})
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
        # 先清理 prdcfg_* 关联表（FK 均为 NO ACTION，需手动删除），再删配置本体
        db.execute(text(
            "DELETE FROM prdcfg_substitutelink WHERE productbaseline_id = :cid"
        ), {"cid": cfg_id})
        db.execute(text(
            "DELETE FROM prdcfg_optionallink WHERE productbaseline_id = :cid"
        ), {"cid": cfg_id})
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

    def _filter_on_link_type(self, db: Session, ws: str, ci_id: str,
                             config_spec, path: str | None,
                             link_type: str, user_login: str,
                             is_admin: bool) -> list:
        """P2-08: 按 P2P linkType 过滤产品结构（最小实现）。

        对齐 Java filterProductStructureOnLinkType 三步骤：
        1. BFS 遍历产品结构，收集所有路径（discoveredPaths）
        2. 查询 CI 的 PathToPathLink（type=linkType），提取 source/target 路径
        3. 仅保留双方路径均在 discoveredPaths 中的链接 → 构建虚拟组件树

        已知限制（MED 最小实现）：
        - 未区分 root/<path> 入口选择（Java 有 path==null/path!=null 两条分支）
        - 路径集合通过全量 BFS 收集（未使用 configSpec PSFilterVisitor 过滤）
        - 返回虚拟根节点（非 Java 的节点替代/补全逻辑）
        """
        # 解析 configSpec 字符串（暂用于路径收集，未在 BFS 中深度使用）
        if isinstance(config_spec, str):
            config_spec = self.parse_config_spec_str(config_spec, db=db,
                                                       user_login=user_login)

        ci = self.get_ci(db, ws, ci_id)

        # 步骤 1: BFS 遍历产品结构，收集所有路径
        discovered_paths = set()
        root_master = db.query(PartMaster).filter(
            PartMaster.workspace_id == ws,
            PartMaster.number == ci.partmaster_partnumber,
        ).first()
        if root_master:
            queue = [(root_master, "-1")]
            while queue:
                pm, pm_path = queue.pop(0)
                rev = pm.last_revision
                if rev is None:
                    continue
                last_it = rev.last_iteration
                if last_it is None:
                    continue
                for link in (last_it.components or []):
                    link_id = link.id
                    from app.models.part import PartSubstituteLink
                    prefix = "s" if isinstance(link, PartSubstituteLink) else "u"
                    child_path = f"{pm_path}-{prefix}{link_id}"
                    discovered_paths.add(child_path)
                    child_master = db.query(PartMaster).filter(
                        PartMaster.workspace_id == link.component_workspace_id,
                        PartMaster.number == link.component_partnumber,
                    ).first()
                    if child_master:
                        queue.append((child_master, child_path))

        if not discovered_paths:
            return []

        # 步骤 2: 查询 CI 的 P2P links（type=linkType）
        p2p_rows = db.execute(text(
            "SELECT ppl.id, ppl.type, ppl.description, ppl.sourcepath, ppl.targetpath "
            "FROM pathtopathlink ppl "
            "JOIN configurationitem_p2plink cp ON cp.pathtopathlink_id = ppl.id "
            "WHERE cp.workspace_id = :ws AND cp.configurationitem_id = :ci "
            "AND ppl.type = :lt"
        ), {"ws": ws, "ci": ci_id, "lt": link_type}).fetchall()

        # 步骤 3: 仅保留双方路径均在 discoveredPaths 中的链接
        valid_links = []
        for r in p2p_rows:
            source_path = r[3]  # sourcepath
            target_path = r[4]  # targetpath
            if source_path in discovered_paths and target_path in discovered_paths:
                valid_links.append(r)

        if not valid_links:
            return []

        # 步骤 4: 构建子组件列表，每个匹配的 P2P target 路径 → 一个组件
        components = []
        for r in valid_links:
            target_path = r[4]
            try:
                decoded = self.decode_path(db, ws, ci_id, target_path)
            except Exception:
                decoded = []
            if not decoded:
                continue
            last_seg = decoded[-1]
            pn = last_seg.get("number", "")
            pm = db.query(PartMaster).filter(
                PartMaster.workspace_id == ws,
                PartMaster.number == pn,
            ).first()
            rev = pm.last_revision if pm and pm.revisions else None
            last_it = rev.last_iteration if rev else None
            components.append({
                "number": pn,
                "name": last_seg.get("name", pn),
                "version": rev.version if rev else "A",
                "iteration": last_it.iteration if last_it else 0,
                "path": target_path,
                "amount": 1.0,
                "unit": None,
                "optional": False,
                "partUsageLinkId": "-1",
                "description": rev.description if rev else "",
                "standardPart": pm.standard_part if pm else False,
                "assembly": bool(last_it and last_it.components) if last_it else False,
                "released": rev.status == 1 if rev else False,
                "obsolete": rev.status == 2 if rev else False,
                "author": self._resolve_user_name(db, pm.author_login) if pm else "",
                "authorLogin": pm.author_login if pm else "",
                "checkOutUser": None,
                "checkOutDate": None,
                "lastIterationNumber": rev.last_iteration_number if rev else 0,
                "virtual": False,
                "substitute": False,
                "partUsageLinkReferenceDescription": None,
                "hasPathData": self._check_has_path_data(db, ws, target_path),
                "accessDeny": False,
                "attributes": [],
                "components": [],
                "substituteIds": [],
                "notifications": self._modification_notifications(db, ws, pn) if pm else [],
            })

        # 虚拟根节点（对齐 Java createVirtualComponent，link_type 非空必有虚拟根）
        root_number = ci.partmaster_partnumber
        root_master = db.query(PartMaster).filter(
            PartMaster.workspace_id == ws,
            PartMaster.number == root_number,
        ).first()
        return [{
            "number": root_number,
            "name": root_master.name if root_master and root_master.name else root_number,
            "version": root_master.last_revision.version if root_master and root_master.revisions else "A",
            "iteration": 0,
            "path": ci_id,
            "amount": 1.0,
            "unit": None,
            "optional": False,
            "partUsageLinkId": "-1",
            "description": "",
            "standardPart": False,
            "assembly": True,
            "released": False,
            "obsolete": False,
            "author": "",
            "authorLogin": "",
            "checkOutUser": None,
            "checkOutDate": None,
            "lastIterationNumber": 0,
            "virtual": True,
            "substitute": False,
            "partUsageLinkReferenceDescription": None,
            "hasPathData": False,
            "accessDeny": False,
            "attributes": [],
            "components": components,
            "substituteIds": [],
            "notifications": [],
        }]

    def delete_instance(self, db: Session, ws: str, ci_id: str, serial: str):
        inst = db.query(ProductInstanceMaster).filter(
            ProductInstanceMaster.workspace_id == ws,
            ProductInstanceMaster.configurationitem_id == ci_id,
            ProductInstanceMaster.serialnumber == serial).first()
        if inst is None:
            raise EntityNotFoundException("ProductInstanceMasterNotFoundException", serial)

        where = {"ws": ws, "ci": ci_id, "sn": serial}

        # 1. 收集 instanceattribute 关联 ID（用于后续孤儿清理）
        attr_rows = db.execute(text(
            "SELECT instanceattribute_id FROM prdinstiteration_attribute "
            "WHERE workspace_id=:ws AND configurationitem_id=:ci "
            "AND prdinstancemaster_serialnumber=:sn"
        ), where).fetchall()
        attr_ids = [r[0] for r in attr_rows]

        # 2. 收集 documentlink 关联 ID（用于后续孤儿清理）
        doclink_rows = db.execute(text(
            "SELECT documentlink_id FROM prdinstiteration_documentlink "
            "WHERE workspace_id=:ws AND configurationitem_id=:ci "
            "AND prdinstancemaster_serialnumber=:sn"
        ), where).fetchall()
        doclink_ids = [r[0] for r in doclink_rows]

        # 3. 删除 7 张 FK 子表（FK 均为 NO ACTION，须先删）
        db.execute(text("DELETE FROM prdinstiteration_attribute "
            "WHERE workspace_id=:ws AND configurationitem_id=:ci "
            "AND prdinstancemaster_serialnumber=:sn"), where)

        db.execute(text("DELETE FROM prdinstiteration_binres "
            "WHERE workspace_id=:ws AND configurationitem_id=:ci "
            "AND prdinstancemaster_serialnumber=:sn"), where)

        db.execute(text("DELETE FROM prdinstiteration_documentlink "
            "WHERE workspace_id=:ws AND configurationitem_id=:ci "
            "AND prdinstancemaster_serialnumber=:sn"), where)

        db.execute(text("DELETE FROM prdinstiteration_p2plink "
            "WHERE workspace_id=:ws AND configurationitem_id=:ci "
            "AND prdinstancemaster_serialnumber=:sn"), where)

        db.execute(text("DELETE FROM prdinstiteration_pathdatamstr "
            "WHERE workspace_id=:ws AND configurationitem_id=:ci "
            "AND prdinstancemaster_serialnumber=:sn"), where)

        db.execute(text("DELETE FROM prdinstanceiteration_optlink "
            "WHERE workspace_id=:ws AND configurationitem_id=:ci "
            "AND prdinstancemaster_serialnumber=:sn"), where)

        db.execute(text("DELETE FROM prdinstanceiteration_sublink "
            "WHERE workspace_id=:ws AND configurationitem_id=:ci "
            "AND prdinstancemaster_serialnumber=:sn"), where)

        # 4. 清理孤儿 instanceattribute（对齐 _replace_instance_attributes 模式）
        for oid in attr_ids:
            still_ref = db.execute(text(
                "SELECT 1 FROM prdinstiteration_attribute "
                "WHERE instanceattribute_id=:id LIMIT 1"
            ), {"id": oid}).first()
            if not still_ref:
                db.execute(text("DELETE FROM instanceattribute WHERE id=:id"), {"id": oid})

        # 5. 清理孤儿 documentlink
        for dlid in doclink_ids:
            still_ref = db.execute(text(
                "SELECT 1 FROM prdinstiteration_documentlink "
                "WHERE documentlink_id=:id LIMIT 1"
            ), {"id": dlid}).first()
            if not still_ref:
                db.execute(text("DELETE FROM documentlink WHERE id=:id"), {"id": dlid})

        # 6. 删除 iteration → master
        db.execute(text("DELETE FROM productinstanceiteration WHERE "
            "workspace_id=:ws AND configurationitem_id=:ci AND "
            "prdinstancemaster_serialnumber=:sn"), where)
        db.delete(inst); db.commit()

    @staticmethod
    def _resolve_pi_config_spec(db: Session, ws: str, ci_id: str, serial: str,
                                 user_login: str = None, diverge: bool = False):
        """解析 pi-{serial} configSpec：通过实例基线获取 baselinedpart 过滤。

        对齐 Java PSFilterManagerBean.getProductInstanceConfigSpec →
        new ResolvedCollectionConfigSpec(productII)。

        实现程度（Tier 2 / 退化策略较"latest"更接近）：
        - 查询 ProductInstanceMaster → 末迭代 → partcollection_id
        - 从 baselinedpart 构建 (workspace, partnumber) → (version, iteration) 映射
        - 返回 _BaselineBasedPSFilter：每个 PartMaster 返回基线的特定迭代（非"latest"）
        - 未实现：optionalUsageLinks / substituteLinks 过滤（ResolvedCollection 完整解析）
        """
        from app.models.product import ProductInstanceIteration

        inst_master = db.query(ProductInstanceMaster).filter(
            ProductInstanceMaster.workspace_id == ws,
            ProductInstanceMaster.serialnumber == serial,
        ).first()
        if not inst_master:
            # 实例不存在 → 降级 latest
            from app.services.configuration.filter.latest_checked_in_ps_filter import LatestCheckedInPSFilter
            return LatestCheckedInPSFilter(diverge=diverge)

        last_it = db.query(ProductInstanceIteration).filter(
            ProductInstanceIteration.workspace_id == ws,
            ProductInstanceIteration.prdinstancemaster_serialnumber == serial,
        ).order_by(ProductInstanceIteration.iteration.desc()).first()
        if not last_it or not last_it.partcollection_id:
            from app.services.configuration.filter.latest_checked_in_ps_filter import LatestCheckedInPSFilter
            return LatestCheckedInPSFilter(diverge=diverge)

        pc_id = last_it.partcollection_id
        bp_rows = db.execute(text(
            "SELECT target_workspace_id, target_partmaster_partnumber, "
            "target_partrevision_version, target_iteration "
            "FROM baselinedpart WHERE partcollection_id = :pcid"
        ), {"pcid": pc_id}).fetchall()

        if not bp_rows:
            from app.services.configuration.filter.latest_checked_in_ps_filter import LatestCheckedInPSFilter
            return LatestCheckedInPSFilter(diverge=diverge)

        baseline_map = {}
        for r in bp_rows:
            key = (r[0], r[1])  # (workspace_id, partnumber)
            baseline_map[key] = (r[2], r[3])  # (version, iteration)

        return _BaselineBasedPSFilter(baseline_map, diverge)


class _BaselineBasedPSFilter:
    """基于基线化零件集合的 PSFilter（Tier-2 实现，优于 "latest" 降级）。

    每个 PartMaster 返回其基线化时的特定 PartIteration。
    未实现 optionalUsageLinks / substituteLinks 过滤（返回名义链接）。
    对齐 Java ResolvedCollectionConfigSpec 的 filterPartIteration 基线查找部分。
    """

    def __init__(self, baseline_map: dict, diverge: bool = False):
        self._baseline_map = baseline_map  # (ws, pn) → (version, iteration)
        self.diverge = diverge

    def filter_part_iterations(self, part_master) -> list:
        key = (part_master.workspace_id, part_master.number)
        target = self._baseline_map.get(key)
        if not target:
            return []
        ver, it = target
        for rev in (part_master.revisions or []):
            if rev.version == ver:
                for iteration in (rev.iterations or []):
                    if iteration.iteration == it:
                        return [iteration]
        return []

    def filter_links(self, path: list) -> list:
        if not path:
            return []
        nominal = path[-1]
        result = [nominal]
        if self.diverge and getattr(nominal, 'substitutes', None):
            for sub in nominal.substitutes:
                result.append(sub)
        return result
