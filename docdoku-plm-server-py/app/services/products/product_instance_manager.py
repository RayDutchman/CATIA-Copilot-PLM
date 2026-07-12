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
    # 序列化辅助
    # ══════════════════════════════════════════════════════════

    def _to_dict(self, m) -> dict:
        return {"serialNumber": m.serialnumber, "workspaceId": m.workspace_id,
                "configurationItemId": m.configurationitem_id}

    def _to_row(self, row) -> dict:
        return {"serialNumber": row[2] if len(row) > 2 else "",
                "workspaceId": row[0] if len(row) > 0 else "",
                "configurationItemId": row[1] if len(row) > 1 else ""}


product_instance_service = ProductInstanceService()
