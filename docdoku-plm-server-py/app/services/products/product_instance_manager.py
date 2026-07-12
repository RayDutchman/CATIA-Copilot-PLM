"""ProductInstanceManager——产品实例管理。

对齐 Java ProductInstanceManagerBean。
底层 delegate 到 ProductStructureService 的实例和 PathData 方法。
"""
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text


class ProductInstanceService:
    """产品实例管理服务。"""

    def __init__(self):
        from app.services.product_structure import ProductStructureService
        self._product = ProductStructureService()

    def list_instances(self, db: Session, ws: str, ci_id: str = None) -> list:
        return [self._to_dict(m) for m in self._product.list_instances(db, ws, ci_id)]

    def get_instance(self, db: Session, ws: str, ci_id: str, serial: str) -> dict:
        m = db.execute(text(
            "SELECT * FROM productinstancemaster "
            "WHERE workspace_id=:ws AND configurationitem_id=:ci AND serialnumber=:sn"
        ), {"ws": ws, "ci": ci_id, "sn": serial}).first()
        if not m:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("ProductInstanceMasterNotFoundException", serial)
        return self._to_row(m)

    def create_instance(self, db: Session, ws: str, ci_id: str, serial: str,
                         baseline_id: int, user_login: str,
                         effectivity_date: datetime = None,
                         effectivity_serial: str = None,
                         effectivity_lot: str = None) -> dict:
        """创建产品实例。可基于已有基线或 effectivity 过滤创建。"""
        return self._to_dict(
            self._product.create_instance(db, ws, ci_id, serial, baseline_id, user_login))

    def update_instance(self, db: Session, ws: str, ci_id: str, serial: str,
                         body: dict, user_login: str = "",
                         iteration: int = None):
        """更新产品实例——迭代备注、属性替换、文档链接。"""
        from app.models.product import ProductInstanceMaster, ProductInstanceIteration

        inst = db.query(ProductInstanceMaster).filter(
            ProductInstanceMaster.workspace_id == ws,
            ProductInstanceMaster.configurationitem_id == ci_id,
            ProductInstanceMaster.serialnumber == serial,
        ).first()
        if not inst:
            from app.core.exceptions import ProductInstanceMasterNotFoundException
            raise ProductInstanceMasterNotFoundException(
                "ProductInstanceMasterNotFoundException", serial)

        if iteration is not None:
            target_it = db.query(ProductInstanceIteration).filter(
                ProductInstanceIteration.workspace_id == ws,
                ProductInstanceIteration.configurationitem_id == ci_id,
                ProductInstanceIteration.prdinstancemaster_serialnumber == serial,
                ProductInstanceIteration.iteration == iteration,
            ).first()
            if not target_it:
                from app.core.exceptions import ProductInstanceIterationNotFoundException
                raise ProductInstanceIterationNotFoundException(
                    "ProductInstanceIterationNotFoundException", serial, str(iteration))
        else:
            target_it = db.query(ProductInstanceIteration).filter(
                ProductInstanceIteration.workspace_id == ws,
                ProductInstanceIteration.configurationitem_id == ci_id,
                ProductInstanceIteration.prdinstancemaster_serialnumber == serial,
            ).order_by(ProductInstanceIteration.iteration.desc()).first()

        if target_it:
            if "description" in body:
                target_it.iteration_note = body["description"]
            if "iterationNote" in body:
                target_it.iteration_note = body["iterationNote"]

            if "instanceAttributes" in body:
                self._replace_instance_attributes(
                    db, ws, ci_id, serial, target_it.iteration,
                    body["instanceAttributes"])

            if "linkedDocuments" in body:
                self._replace_linked_documents(
                    db, ws, ci_id, serial, target_it.iteration,
                    body["linkedDocuments"])

        db.commit()
        return {"serialNumber": serial}

    def delete_instance(self, db: Session, ws: str, ci_id: str, serial: str):
        return self._product.delete_instance(db, ws, ci_id, serial)

    def rebase_instance(self, db: Session, ws: str, ci_id: str, serial: str,
                         baseline_id: int, user_login: str):
        """产品实例换基线——创建新迭代并关联新基线。"""
        from app.models.product import ProductInstanceMaster, ProductInstanceIteration

        inst = db.query(ProductInstanceMaster).filter(
            ProductInstanceMaster.workspace_id == ws,
            ProductInstanceMaster.configurationitem_id == ci_id,
            ProductInstanceMaster.serialnumber == serial,
        ).first()
        if not inst:
            from app.core.exceptions import ProductInstanceMasterNotFoundException
            raise ProductInstanceMasterNotFoundException(
                "ProductInstanceMasterNotFoundException", serial)

        bl_exists = db.execute(text(
            "SELECT 1 FROM productbaseline WHERE id=:bid"
        ), {"bid": baseline_id}).first()
        if not bl_exists:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("BaselineNotFoundException", str(baseline_id))

        last_it = db.query(ProductInstanceIteration).filter(
            ProductInstanceIteration.workspace_id == ws,
            ProductInstanceIteration.configurationitem_id == ci_id,
            ProductInstanceIteration.prdinstancemaster_serialnumber == serial,
        ).order_by(ProductInstanceIteration.iteration.desc()).first()

        next_it = (last_it.iteration + 1) if last_it else 1
        new_iteration = ProductInstanceIteration(
            workspace_id=ws,
            configurationitem_id=ci_id,
            prdinstancemaster_serialnumber=serial,
            iteration=next_it,
            productbaseline_id=baseline_id,
            author_workspace_id=ws,
            author_login=user_login,
            creation_date=datetime.utcnow(),
            iteration_note=last_it.iteration_note if last_it else "",
        )
        db.add(new_iteration)
        db.commit()

    def get_instance_iterations(self, db: Session, ws: str, ci_id: str,
                                 serial: str) -> list:
        """获取产品实例的所有迭代。"""
        rows = db.execute(text(
            "SELECT * FROM productinstanceiteration "
            "WHERE workspace_id=:ws AND configurationitem_id=:ci "
            "AND prdinstancemaster_serialnumber=:sn ORDER BY iteration"
        ), {"ws": ws, "ci": ci_id, "sn": serial}).fetchall()
        return [{"iteration": r[0], "note": r[1] if len(r) > 1 else "",
                 "author": r[2] if len(r) > 2 else "",
                 "creationDate": str(r[3]) if len(r) > 3 else "",
                 "baselineId": r[4] if len(r) > 4 else None}
                for r in rows]

    def get_path_data_masters(self, db: Session, ws: str, ci_id: str,
                               serial: str) -> list:
        """获取产品实例的所有 PathDataMaster。"""
        rows = db.execute(text(
            "SELECT * FROM pathdatamaster "
            "WHERE workspace_id=:ws AND configurationitem_id=:ci "
            "AND prdinstancemaster_serialnumber=:sn"
        ), {"ws": ws, "ci": ci_id, "sn": serial}).fetchall()
        return [{"id": r[0], "path": r[1] if len(r) > 1 else "",
                 "name": r[2] if len(r) > 2 else "",
                 "description": r[3] if len(r) > 3 else ""}
                for r in rows]

    # ══════════════════════════════════════════════════════════
    # 私有辅助方法
    # ══════════════════════════════════════════════════════════

    @staticmethod
    def _infer_attr_dtype(attr: dict) -> str:
        """根据属性值字段推断 JPA dtype 鉴别值。"""
        if attr.get("dtype") or attr.get("typeName"):
            return attr.get("dtype") or attr.get("typeName")
        if attr.get("booleanValue") is not None:
            return "InstanceBooleanAttribute"
        if attr.get("dateValue") is not None:
            return "InstanceDateAttribute"
        if attr.get("numberValue") is not None:
            return "InstanceNumberAttribute"
        if attr.get("urlValue") is not None:
            return "InstanceURLAttribute"
        if attr.get("indexValue") is not None:
            return "InstanceListOfValuesAttribute"
        if attr.get("longTextValue") is not None:
            return "InstanceLongTextAttribute"
        return "InstanceTextAttribute"

    def _replace_instance_attributes(self, db: Session, ws: str, ci_id: str,
                                       sn: str, iteration: int, attrs: list):
        """全量替换指定迭代的实例属性（对齐 Java 就地更新模式）。"""
        old_ids = [
            row[0] for row in db.execute(text(
                "SELECT instanceattribute_id FROM prdinstiteration_attribute "
                "WHERE workspace_id=:ws AND configurationitem_id=:ci "
                "AND prdinstancemaster_serialnumber=:sn AND iteration=:it"
            ), {"ws": ws, "ci": ci_id, "sn": sn, "it": iteration}).fetchall()
        ]
        db.execute(text(
            "DELETE FROM prdinstiteration_attribute "
            "WHERE workspace_id=:ws AND configurationitem_id=:ci "
            "AND prdinstancemaster_serialnumber=:sn AND iteration=:it"
        ), {"ws": ws, "ci": ci_id, "sn": sn, "it": iteration})
        for oid in old_ids:
            still_ref = db.execute(text(
                "SELECT 1 FROM prdinstiteration_attribute "
                "WHERE instanceattribute_id=:id LIMIT 1"
            ), {"id": oid}).first()
            if still_ref:
                continue
            db.execute(text("DELETE FROM instanceattribute WHERE id=:id"), {"id": oid})
        for order, attr in enumerate(attrs):
            dtype = self._infer_attr_dtype(attr)
            result = db.execute(text(
                "INSERT INTO instanceattribute (name, mandatory, locked, dtype, "
                "booleanvalue, datevalue, indexvalue, numbervalue, "
                "textvalue, longtextvalue, urlvalue) "
                "VALUES (:name, :mand, :locked, :dtype, "
                ":bv, :dv, :iv, :nv, :tv, :ltv, :uv) RETURNING id"
            ), {
                "name": attr.get("name", ""),
                "mand": attr.get("mandatory", False),
                "locked": attr.get("locked", False),
                "dtype": dtype,
                "bv": attr.get("booleanValue"),
                "dv": attr.get("dateValue"),
                "iv": attr.get("indexValue"),
                "nv": attr.get("numberValue"),
                "tv": attr.get("textValue"),
                "ltv": attr.get("longTextValue"),
                "uv": attr.get("urlValue"),
            })
            attr_id = result.fetchone()[0]
            db.execute(text(
                "INSERT INTO prdinstiteration_attribute "
                "(prdinstancemaster_serialnumber, configurationitem_id, "
                "workspace_id, iteration, instanceattribute_id, attribute_order) "
                "VALUES (:sn, :ci, :ws, :it, :aid, :ord)"
            ), {"sn": sn, "ci": ci_id, "ws": ws, "it": iteration,
                "aid": attr_id, "ord": order})

    def _replace_linked_documents(self, db: Session, ws: str, ci_id: str,
                                    sn: str, iteration: int, linked_docs: list):
        """全量替换指定迭代的关联文档。"""
        db.execute(text(
            "DELETE FROM prdinstiteration_documentlink "
            "WHERE workspace_id=:ws AND configurationitem_id=:ci "
            "AND prdinstancemaster_serialnumber=:sn AND iteration=:it"
        ), {"ws": ws, "ci": ci_id, "sn": sn, "it": iteration})
        for dl in linked_docs:
            dm_id = dl.get("documentMasterId", "")
            ver = dl.get("version", "")
            if not dm_id:
                continue
            result = db.execute(text(
                "INSERT INTO documentlink "
                "(target_documentmaster_id, target_docrevision_version, "
                "target_workspace_id, commentdata) "
                "VALUES (:dm, :ver, :tws, :comment) RETURNING id"
            ), {"dm": dm_id, "ver": ver, "tws": ws,
                "comment": dl.get("comment", dl.get("commentLink", "")) or ""})
            dl_id = result.fetchone()[0]
            db.execute(text(
                "INSERT INTO prdinstiteration_documentlink "
                "(workspace_id, configurationitem_id, prdinstancemaster_serialnumber, "
                "iteration, documentlink_id) "
                "VALUES (:ws, :ci, :sn, :it, :dlid)"
            ), {"ws": ws, "ci": ci_id, "sn": sn, "it": iteration, "dlid": dl_id})

    # ══════════════════════════════════════════════════════════
    # 完整 DTO 构建（从 products.py 迁移）
    # ══════════════════════════════════════════════════════════

    def build_master_dto(self, db: Session, inst,
                          svc=None) -> dict:
        """构建完整 ProductInstanceMasterDTO（identifier + acl + iteration 列表）。

        对齐 Java ProductInstanceMasterDTO（serialNumber/configurationItemId/identifier/
        productInstanceIterations/acl）。P2-07：list_product_instances / list_ci_instances
        复用此函数输出完整 DTO。
        """
        from app.models.util.date_utils import format_iso_date
        from app.models.security import ACL, AclUserEntry, AclUserGroupEntry
        from app.models.configuration.product_instance_iteration import ProductInstanceIteration
        from app.models.configuration.product_baseline import ProductBaseline
        from app.services.products.path_to_path_service import path_to_path_service

        ws = inst.workspace_id
        sn = inst.serialnumber
        ci_id = inst.configurationitem_id

        # ── acl ──
        acl_data = None
        if inst.acl_id:
            acl = db.query(ACL).filter(ACL.id == inst.acl_id).first()
            if acl:
                user_entries = db.query(AclUserEntry).filter(AclUserEntry.acl_id == inst.acl_id).all()
                group_entries = db.query(AclUserGroupEntry).filter(AclUserGroupEntry.acl_id == inst.acl_id).all()
                _PERM = {0: "FORBIDDEN", 1: "READ_ONLY", 2: "FULL_ACCESS"}
                acl_data = {
                    "userEntries": [
                        {"key": e.principal_login, "value": _PERM.get(e.permission, "FORBIDDEN")}
                        for e in user_entries
                    ],
                    "groupEntries": [
                        {"key": e.principal_id, "value": _PERM.get(e.permission, "FORBIDDEN")}
                        for e in group_entries
                    ],
                }

        # ── iterations ──
        iterations = db.query(ProductInstanceIteration).filter(
            ProductInstanceIteration.workspace_id == ws,
            ProductInstanceIteration.prdinstancemaster_serialnumber == sn,
        ).order_by(ProductInstanceIteration.iteration).all()

        if svc is None:
            from app.services.product_structure import ProductStructureService
            svc = ProductStructureService()

        iterations_list = []
        for it in iterations:
            it_num = it.iteration

            sub_rows = db.execute(text(
                "SELECT substitutelinks FROM prdinstanceiteration_sublink "
                "WHERE workspace_id=:ws AND configurationitem_id=:ci "
                "AND prdinstancemaster_serialnumber=:sn AND iteration=:it"
            ), {"ws": ws, "ci": ci_id, "sn": sn, "it": it_num}).fetchall()
            substitute_links = [r[0] for r in sub_rows if r[0]]

            opt_rows = db.execute(text(
                "SELECT optionalusagelinks FROM prdinstanceiteration_optlink "
                "WHERE workspace_id=:ws AND configurationitem_id=:ci "
                "AND prdinstancemaster_serialnumber=:sn AND iteration=:it"
            ), {"ws": ws, "ci": ci_id, "sn": sn, "it": it_num}).fetchall()
            optional_links = [r[0] for r in opt_rows if r[0]]

            substitutes_parts = []
            for path_str in substitute_links:
                try:
                    decoded = svc.decode_path(db, ws, ci_id, path_str)
                    if decoded:
                        substitutes_parts.append({"partLinks": decoded})
                except Exception:
                    pass

            optionals_parts = []
            for path_str in optional_links:
                try:
                    decoded = svc.decode_path(db, ws, ci_id, path_str)
                    if decoded:
                        optionals_parts.append({"partLinks": decoded})
                except Exception:
                    pass

            pdm_rows = db.execute(text(
                "SELECT pdm.id, pdm.path FROM pathdatamaster pdm "
                "JOIN prdinstiteration_pathdatamstr pipd ON pipd.pathdatamaster_id = pdm.id "
                "WHERE pipd.workspace_id=:ws AND pipd.configurationitem_id=:ci "
                "AND pipd.prdinstancemaster_serialnumber=:sn "
                "AND pipd.prdinstanceiteration_iteration=:it"
            ), {"ws": ws, "ci": ci_id, "sn": sn, "it": it_num}).fetchall()
            path_data_masters = [{"id": r[0], "path": r[1]} for r in pdm_rows]

            path_data_paths = []
            for pdm in path_data_masters:
                try:
                    decoded = svc.decode_path(db, ws, ci_id, pdm["path"])
                    if decoded:
                        path_data_paths.append({"partLinks": decoded})
                except Exception:
                    pass

            p2p_rows = db.execute(text(
                "SELECT ppl.id, ppl.type, ppl.description, ppl.sourcepath, ppl.targetpath "
                "FROM pathtopathlink ppl "
                "JOIN prdinstiteration_p2plink pip ON pip.pathtopathlink_id = ppl.id "
                "WHERE pip.workspace_id=:ws AND pip.configurationitem_id=:ci "
                "AND pip.prdinstancemaster_serialnumber=:sn AND pip.iteration=:it"
            ), {"ws": ws, "ci": ci_id, "sn": sn, "it": it_num}).fetchall()
            path_to_path_links = [
                path_to_path_service._link_row_to_dict(r, db=db, ws=ws, ci_id=ci_id)
                for r in p2p_rows
            ]

            based_on = None
            if it.productbaseline_id:
                baseline = db.query(ProductBaseline).filter(
                    ProductBaseline.id == it.productbaseline_id,
                ).first()
                if baseline:
                    based_on = {
                        "id": baseline.id,
                        "name": baseline.name,
                        "description": baseline.description,
                    }

            attr_rows = db.execute(text(
                "SELECT ia.id, ia.name, ia.mandatory, ia.locked, ia.booleanvalue, "
                "ia.datevalue, ia.indexvalue, ia.numbervalue, ia.textvalue, "
                "ia.longtextvalue, ia.urlvalue "
                "FROM instanceattribute ia "
                "JOIN prdinstiteration_attribute pia ON pia.instanceattribute_id = ia.id "
                "WHERE pia.workspace_id=:ws AND pia.configurationitem_id=:ci "
                "AND pia.prdinstancemaster_serialnumber=:sn AND pia.iteration=:it "
                "ORDER BY pia.attribute_order"
            ), {"ws": ws, "ci": ci_id, "sn": sn, "it": it_num}).fetchall()
            instance_attrs = [{
                "id": r[0], "name": r[1], "mandatory": r[2], "locked": r[3],
                "booleanValue": r[4],
                "dateValue": str(r[5]) if r[5] else None,
                "indexValue": r[6], "numberValue": r[7],
                "textValue": r[8], "longTextValue": r[9], "urlValue": r[10],
            } for r in attr_rows]

            doc_rows = db.execute(text(
                "SELECT dl.id, dl.target_documentmaster_id, dl.target_docrevision_version, "
                "dl.target_workspace_id, dl.commentdata "
                "FROM documentlink dl "
                "JOIN prdinstiteration_documentlink pid ON pid.documentlink_id = dl.id "
                "WHERE pid.workspace_id=:ws AND pid.configurationitem_id=:ci "
                "AND pid.prdinstancemaster_serialnumber=:sn AND pid.iteration=:it"
            ), {"ws": ws, "ci": ci_id, "sn": sn, "it": it_num}).fetchall()
            linked_docs = [{
                "id": r[0], "documentMasterId": r[1], "version": r[2],
                "workspaceId": r[3], "commentLink": r[4] or "",
            } for r in doc_rows]

            file_rows = db.execute(text(
                "SELECT br.fullname, br.dtype, br.contentlength, br.lastmodified, "
                "br.quality, br.x_max, br.x_min, br.y_max, br.y_min, br.z_max, br.z_min "
                "FROM binaryresource br "
                "JOIN prdinstiteration_binres pib ON pib.attachedfile_fullname = br.fullname "
                "WHERE pib.workspace_id=:ws AND pib.configurationitem_id=:ci "
                "AND pib.prdinstancemaster_serialnumber=:sn AND pib.iteration=:it"
            ), {"ws": ws, "ci": ci_id, "sn": sn, "it": it_num}).fetchall()
            attached_files = [{
                "fullName": r[0], "type": r[1], "contentLength": r[2],
                "lastModified": str(r[3]) if r[3] else None,
                "quality": r[4], "xMax": r[5], "xMin": r[6],
                "yMax": r[7], "yMin": r[8], "zMax": r[9], "zMin": r[10],
            } for r in file_rows]

            iterations_list.append({
                "iteration": it_num,
                "iterationNote": it.iteration_note,
                "creationDate": format_iso_date(it.creation_date),
                "modificationDate": format_iso_date(it.modification_date),
                "author": self._get_user_dto_inline(db, it.author_login, ws),
                "substituteLinks": substitute_links,
                "optionalUsageLinks": optional_links,
                "substitutesParts": substitutes_parts,
                "optionalsParts": optionals_parts,
                "pathDataMasterList": path_data_masters,
                "pathDataPaths": path_data_paths,
                "pathToPathLinks": path_to_path_links,
                "basedOn": based_on,
                "instanceAttributes": instance_attrs,
                "linkedDocuments": linked_docs,
                "attachedFiles": attached_files,
            })

        return {
            "serialNumber": sn,
            "configurationItemId": ci_id,
            "identifier": f"{ws}/{ci_id}-{sn}",
            "acl": acl_data,
            "productInstanceIterations": iterations_list,
        }

    # ══════════════════════════════════════════════════════════
    # 序列化辅助
    # ══════════════════════════════════════════════════════════

    @staticmethod
    def _get_user_dto_inline(db: Session, login: str, ws: str) -> dict:
        if not login:
            return {"login": "", "name": "", "email": None, "language": None, "workspaceId": ws}
        from app.models.auth import Account
        acc = db.query(Account).filter(Account.login == login).first()
        name = acc.name if (acc and acc.name) else login
        return {"login": login, "name": name, "email": None, "language": None, "workspaceId": ws}

    def _to_dict(self, m) -> dict:
        return {"serialNumber": m.serialnumber, "workspaceId": m.workspace_id,
                "configurationItemId": m.configurationitem_id}

    def _to_row(self, row) -> dict:
        return {"serialNumber": row[2] if len(row) > 2 else "",
                "workspaceId": row[0] if len(row) > 0 else "",
                "configurationItemId": row[1] if len(row) > 1 else ""}


product_instance_service = ProductInstanceService()
