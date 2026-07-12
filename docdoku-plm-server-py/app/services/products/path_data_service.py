"""PathData CRUD Service。

对齐 Payara ProductInstanceManagerBean 的 PathData 相关方法。
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text


class PathDataService:
    """PathDataMaster / PathDataIteration 的创建、读取、更新、删除。"""

    # ─────────────────────────────────────────
    # 查询
    # ─────────────────────────────────────────

    @staticmethod
    def _infer_attr_dtype(attr: dict) -> str:
        """根据属性值字段推断 JPA dtype 鉴别值（对齐 product_instances._infer_attr_dtype）。"""
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

    def get_path_data_masters(self, db: Session, ws: str, ci_id: str, sn: str) -> list:
        """获取产品实例下所有 PathDataMaster，含迭代列表。"""
        rows = db.execute(text(
            "SELECT pdm.id, pdm.path "
            "FROM pathdatamaster pdm "
            "JOIN prdinstiteration_pathdatamstr pipd ON pipd.pathdatamaster_id = pdm.id "
            "WHERE pipd.workspace_id = :ws "
            "  AND pipd.configurationitem_id = :ci "
            "  AND pipd.prdinstancemaster_serialnumber = :sn"
        ), {"ws": ws, "ci": ci_id, "sn": sn}).fetchall()
        return [{"id": r[0], "path": r[1]} for r in rows]

    def get_path_data_master_by_id(self, db: Session, master_id: int) -> Optional[dict]:
        """按 ID 加载 PathDataMaster。"""
        row = db.execute(text(
            "SELECT id, path FROM pathdatamaster WHERE id = :id"
        ), {"id": master_id}).first()
        return {"id": row[0], "path": row[1]} if row else None

    def get_path_data_by_path(self, db: Session, ws: str, ci_id: str,
                               sn: str, path: str) -> Optional[dict]:
        """按路径字符串查找 PathDataMaster（找不到返回 None，不抛异常）。"""
        row = db.execute(text(
            "SELECT pdm.id, pdm.path "
            "FROM pathdatamaster pdm "
            "JOIN prdinstiteration_pathdatamstr pipd ON pipd.pathdatamaster_id = pdm.id "
            "WHERE pipd.workspace_id = :ws "
            "  AND pipd.configurationitem_id = :ci "
            "  AND pipd.prdinstancemaster_serialnumber = :sn "
            "  AND pdm.path = :path"
        ), {"ws": ws, "ci": ci_id, "sn": sn, "path": path}).first()
        return {"id": row[0], "path": row[1]} if row else None

    def get_path_data_iterations(self, db: Session, master_id: int) -> list:
        """获取 PathDataMaster 的所有迭代，按迭代号升序。"""
        rows = db.execute(text(
            "SELECT iteration, pathdatamaster_id, dateiteration, iterationnote "
            "FROM pathdataiteration "
            "WHERE pathdatamaster_id = :mid "
            "ORDER BY iteration ASC"
        ), {"mid": master_id}).fetchall()
        return [self._iter_row_to_dict(r) for r in rows]

    def get_path_data_iteration(self, db: Session, master_id: int, iteration: int) -> Optional[dict]:
        """获取指定迭代。"""
        row = db.execute(text(
            "SELECT iteration, pathdatamaster_id, dateiteration, iterationnote "
            "FROM pathdataiteration "
            "WHERE pathdatamaster_id = :mid AND iteration = :it"
        ), {"mid": master_id, "it": iteration}).first()
        return self._iter_row_to_dict(row) if row else None

    def get_attributes_for_iteration(self, db: Session, master_id: int, iteration: int) -> list:
        """获取 PathDataIteration 的实例属性列表。"""
        rows = db.execute(text(
            "SELECT ia.id, ia.name, ia.mandatory, ia.locked, "
            "ia.booleanvalue, ia.datevalue, ia.indexvalue, ia.numbervalue, "
            "ia.textvalue, ia.longtextvalue, ia.urlvalue "
            "FROM instanceattribute ia "
            "JOIN pathdataiteration_attribute pdia "
            "  ON pdia.instanceattribute_id = ia.id "
            "WHERE pdia.pathdata_iteration = :it "
            "  AND pdia.pathdatamaster_id = :mid "
            "ORDER BY pdia.attribute_order"
        ), {"it": iteration, "mid": master_id}).fetchall()
        return [self._attr_row_to_dict(r) for r in rows]

    # ─────────────────────────────────────────
    # 创建
    # ─────────────────────────────────────────

    def create_path_data_master(self, db: Session, ws: str, ci_id: str,
                                 sn: str, path: str,
                                 attrs: list, note: str) -> dict:
        """创建 PathDataMaster（首迭代）。
        
        若同路径 master 已存在 → 追加新迭代（对齐 Java createPathDataMaster 逻辑）。
        要求产品实例必须存在（有 productinstanceiteration 记录）。
        """
        from app.core.exceptions import EntityNotFoundException

        # 验证产品实例存在
        iter_row = db.execute(text(
            "SELECT iteration FROM productinstanceiteration "
            "WHERE workspace_id = :ws AND configurationitem_id = :ci "
            "AND prdinstancemaster_serialnumber = :sn "
            "ORDER BY iteration DESC LIMIT 1"
        ), {"ws": ws, "ci": ci_id, "sn": sn}).first()
        if not iter_row:
            raise EntityNotFoundException("ProductInstanceMasterNotFoundException", sn)

        # 查是否已存在同路径 master
        existing = self.get_path_data_by_path(db, ws, ci_id, sn, path)
        if existing:
            # 已存在 → 追加新迭代
            master_id = existing["id"]
            self._append_iteration(db, master_id, attrs, note)
            db.commit()
            return self._build_master_dict(db, ws, ci_id, sn, master_id)

        # 新建 master
        result = db.execute(text(
            "INSERT INTO pathdatamaster (path) VALUES (:path) RETURNING id"
        ), {"path": path})
        master_id = result.fetchone()[0]

        # 挂到产品实例最新迭代
        self._attach_master_to_instance(db, ws, ci_id, sn, master_id)

        # 创建首迭代
        self._append_iteration(db, master_id, attrs, note, iteration=1)
        db.commit()
        return self._build_master_dict(db, ws, ci_id, sn, master_id)

    def add_new_path_data_iteration(self, db: Session, ws: str, ci_id: str,
                                     sn: str, master_id: int,
                                     attrs: list, note: str,
                                     linked_docs: list = None) -> dict:
        """追加一个新 PathDataIteration（对齐 Java addNewPathDataIteration）。"""
        master = self.get_path_data_master_by_id(db, master_id)
        if not master:
            from app.core.exceptions import PathDataMasterNotFoundException
            raise PathDataMasterNotFoundException("PathDataMasterNotFoundException", str(master_id))

        # 确认 master 属于此产品实例
        self._verify_master_belongs_to_instance(db, ws, ci_id, sn, master_id)

        self._append_iteration(db, master_id, attrs, note,
                               linked_docs=linked_docs or [])
        db.commit()
        return self._build_master_dict(db, ws, ci_id, sn, master_id)

    # ─────────────────────────────────────────
    # 更新
    # ─────────────────────────────────────────

    def update_path_data(self, db: Session, ws: str, ci_id: str,
                          sn: str, master_id: int, iteration: int,
                          attrs: list, note: str,
                          linked_docs: list = None) -> dict:
        """更新指定 PathDataIteration 的属性/备注/文档链接。"""
        master = self.get_path_data_master_by_id(db, master_id)
        if not master:
            from app.core.exceptions import PathDataMasterNotFoundException
            raise PathDataMasterNotFoundException("PathDataMasterNotFoundException", str(master_id))

        self._verify_master_belongs_to_instance(db, ws, ci_id, sn, master_id)

        # 更新 iterationnote
        db.execute(text(
            "UPDATE pathdataiteration SET iterationnote = :note "
            "WHERE pathdatamaster_id = :mid AND iteration = :it"
        ), {"note": note, "mid": master_id, "it": iteration})

        # 同步属性
        self._sync_path_data_attributes(db, master_id, iteration, attrs)

        # 同步文档链接
        if linked_docs is not None:
            self._sync_linked_documents(db, master_id, iteration, linked_docs)

        db.commit()
        return self._build_master_dict(db, ws, ci_id, sn, master_id)

    # ─────────────────────────────────────────
    # 删除
    # ─────────────────────────────────────────

    def delete_path_data(self, db: Session, ws: str, ci_id: str,
                          sn: str, master_id: int) -> None:
        """删除 PathDataMaster 及其所有迭代（级联删附件与属性）。"""
        master = self.get_path_data_master_by_id(db, master_id)
        if not master:
            from app.core.exceptions import PathDataMasterNotFoundException
            raise PathDataMasterNotFoundException("PathDataMasterNotFoundException", str(master_id))

        self._verify_master_belongs_to_instance(db, ws, ci_id, sn, master_id)

        # 清理属性关联表
        db.execute(text(
            "DELETE FROM pathdataiteration_attribute "
            "WHERE pathdatamaster_id = :mid"
        ), {"mid": master_id})

        # 删除迭代
        db.execute(text(
            "DELETE FROM pathdataiteration WHERE pathdatamaster_id = :mid"
        ), {"mid": master_id})

        # 清理文档链接关联表
        db.execute(text(
            "DELETE FROM pathdataiteration_documentlink "
            "WHERE pathdatamaster_id = :mid"
        ), {"mid": master_id})

        # 解除与产品实例的关联
        db.execute(text(
            "DELETE FROM prdinstiteration_pathdatamstr "
            "WHERE pathdatamaster_id = :mid"
        ), {"mid": master_id})

        # 清理引用此路径的 P2P links（source 或 target 指向该路径的 links 变成悬挂引用）
        # 对齐 Java ProductManagerBean.removeObsoletePathToPathLinks() 行为
        deleted_path = master["path"]
        if deleted_path:
            # 先找出需要删除的 link id
            orphan_links = db.execute(text(
                "SELECT id FROM pathtopathlink "
                "WHERE sourcepath = :p OR targetpath = :p"
            ), {"p": deleted_path}).fetchall()
            for link_row in orphan_links:
                link_id = link_row[0]
                db.execute(text(
                    "DELETE FROM configurationitem_p2plink "
                    "WHERE pathtopathlink_id = :lid"
                ), {"lid": link_id})
                db.execute(text(
                    "DELETE FROM productbaseline_p2plink "
                    "WHERE pathtopathlink_id = :lid"
                ), {"lid": link_id})
                db.execute(text(
                    "DELETE FROM prdinstiteration_p2plink "
                    "WHERE pathtopathlink_id = :lid"
                ), {"lid": link_id})
                db.execute(text(
                    "DELETE FROM pathtopathlink WHERE id = :lid"
                ), {"lid": link_id})

        # 删除 master
        db.execute(text(
            "DELETE FROM pathdatamaster WHERE id = :mid"
        ), {"mid": master_id})

        db.commit()

    # ─────────────────────────────────────────
    # 内部工具方法
    # ─────────────────────────────────────────

    def _append_iteration(self, db: Session, master_id: int,
                           attrs: list, note: str,
                           iteration: int = None,
                           linked_docs: list = None):
        """追加迭代：自动确定下一迭代号，写 DB，同步属性。"""
        if iteration is None:
            max_row = db.execute(text(
                "SELECT MAX(iteration) FROM pathdataiteration "
                "WHERE pathdatamaster_id = :mid"
            ), {"mid": master_id}).first()
            iteration = (max_row[0] or 0) + 1

        db.execute(text(
            "INSERT INTO pathdataiteration (iteration, pathdatamaster_id, "
            "dateiteration, iterationnote) "
            "VALUES (:it, :mid, :dt, :note)"
        ), {"it": iteration, "mid": master_id,
            "dt": datetime.utcnow(), "note": note})

        # 写属性
        self._sync_path_data_attributes(db, master_id, iteration, attrs or [])

        # 写文档链接
        if linked_docs:
            self._sync_linked_documents(db, master_id, iteration, linked_docs)

    def _attach_master_to_instance(self, db: Session, ws: str, ci_id: str,
                                    sn: str, master_id: int):
        """将 PathDataMaster 挂到产品实例最新迭代的关联表。"""
        # 获取最新迭代号
        iter_row = db.execute(text(
            "SELECT iteration FROM productinstanceiteration "
            "WHERE workspace_id = :ws AND configurationitem_id = :ci "
            "AND prdinstancemaster_serialnumber = :sn "
            "ORDER BY iteration DESC LIMIT 1"
        ), {"ws": ws, "ci": ci_id, "sn": sn}).first()
        if not iter_row:
            return
        pii_iteration = iter_row[0]

        db.execute(text(
            "INSERT INTO prdinstiteration_pathdatamstr "
            "(workspace_id, configurationitem_id, prdinstancemaster_serialnumber, "
            "iteration, pathdatamaster_id) "
            "VALUES (:ws, :ci, :sn, :it, :mid) "
            "ON CONFLICT DO NOTHING"
        ), {"ws": ws, "ci": ci_id, "sn": sn,
            "it": pii_iteration, "mid": master_id})

    def _verify_master_belongs_to_instance(self, db: Session, ws: str,
                                            ci_id: str, sn: str, master_id: int):
        """验证 PathDataMaster 确实属于此产品实例（否则抛 404）。"""
        row = db.execute(text(
            "SELECT 1 FROM prdinstiteration_pathdatamstr "
            "WHERE workspace_id = :ws AND configurationitem_id = :ci "
            "AND prdinstancemaster_serialnumber = :sn "
            "AND pathdatamaster_id = :mid"
        ), {"ws": ws, "ci": ci_id, "sn": sn, "mid": master_id}).first()
        if not row:
            from app.core.exceptions import PathDataMasterNotFoundException
            raise PathDataMasterNotFoundException("PathDataMasterNotFoundException", str(master_id))

    def _sync_path_data_attributes(self, db: Session, master_id: int,
                                    iteration: int, attrs: list):
        """同步 PathDataIteration 的实例属性（先删后建）。"""
        # 查旧属性 ID
        old_ids = [
            row[0] for row in db.execute(text(
                "SELECT instanceattribute_id FROM pathdataiteration_attribute "
                "WHERE pathdatamaster_id = :mid AND pathdata_iteration = :it"
            ), {"mid": master_id, "it": iteration}).fetchall()
        ]
        # 清除关联
        db.execute(text(
            "DELETE FROM pathdataiteration_attribute "
            "WHERE pathdatamaster_id = :mid AND pathdata_iteration = :it"
        ), {"mid": master_id, "it": iteration})
        # 删孤儿属性
        for oid in old_ids:
            db.execute(text("DELETE FROM instanceattribute WHERE id = :id"), {"id": oid})

        # 插入新属性
        for order, attr in enumerate(attrs):
            dtype = self._infer_attr_dtype(attr)
            result = db.execute(text(
                "INSERT INTO instanceattribute "
                "(name, mandatory, locked, dtype, booleanvalue, datevalue, indexvalue, "
                "numbervalue, textvalue, longtextvalue, urlvalue) "
                "VALUES (:name, :mand, :locked, :dtype, :bv, :dv, :iv, :nv, :tv, :ltv, :uv) "
                "RETURNING id"
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
                "INSERT INTO pathdataiteration_attribute "
                "(pathdata_iteration, pathdatamaster_id, instanceattribute_id, attribute_order) "
                "VALUES (:it, :mid, :aid, :order)"
            ), {"it": iteration, "mid": master_id, "aid": attr_id, "order": order})

    def _sync_linked_documents(self, db: Session, master_id: int,
                                 iteration: int, linked_docs: list):
        """同步 PathDataIteration 关联的文档（先删后建）。

        表结构：pathdataiteration_documentlink(pathdata_iteration, pathdatamaster_id, documentlink_id)
        关联通过 documentlink 中间表（同 partiteration_documentlink 模式）。
        """
        # 清除旧关联（但不删 documentlink 本身，可能被其他表共用）
        db.execute(text(
            "DELETE FROM pathdataiteration_documentlink "
            "WHERE pathdatamaster_id = :mid AND pathdata_iteration = :it"
        ), {"mid": master_id, "it": iteration})

        for doc in linked_docs:
            dm_id = doc.get("documentMasterId", "")
            ver = doc.get("version", "")
            ws_id = doc.get("workspaceId", "")
            comment = doc.get("commentLink", doc.get("comment", ""))
            if not dm_id:
                continue
            # 创建 documentlink 记录
            result = db.execute(text(
                "INSERT INTO documentlink "
                "(target_documentmaster_id, target_docrevision_version, "
                "target_workspace_id, commentdata) "
                "VALUES (:dm, :ver, :ws, :comment) RETURNING id"
            ), {"dm": dm_id, "ver": ver, "ws": ws_id, "comment": comment or ""})
            dl_id = result.fetchone()[0]
            # 关联到 pathdataiteration
            db.execute(text(
                "INSERT INTO pathdataiteration_documentlink "
                "(pathdata_iteration, pathdatamaster_id, documentlink_id) "
                "VALUES (:it, :mid, :dlid)"
            ), {"it": iteration, "mid": master_id, "dlid": dl_id})

    def _build_master_dict(self, db: Session, ws: str, ci_id: str,
                            sn: str, master_id: int) -> dict:
        """构建完整 PathDataMasterDTO dict。"""
        master = self.get_path_data_master_by_id(db, master_id)
        if not master:
            return {"id": master_id, "path": "", "pathDataIterations": []}

        iterations_raw = self.get_path_data_iterations(db, master_id)
        iterations = []
        for it in iterations_raw:
            attrs = self.get_attributes_for_iteration(db, master_id, it["iteration"])
            iterations.append({
                "serialNumber": sn,
                "pathDataMasterId": master_id,
                "iteration": it["iteration"],
                "iterationNote": it["iterationNote"],
                "path": master["path"],
                "attachedFiles": [],
                "linkedDocuments": [],
                "instanceAttributes": attrs,
            })

        # 对齐 Java getPathData：填充 partLinksList / partAttributes / partAttributeTemplates
        part_links_list = None
        part_attrs = []
        part_attr_templates = []
        last_pn = None
        last_pv = None
        try:
            from app.services.product_structure import ProductStructureService
            _svc = ProductStructureService()
            decoded = _svc.decode_path(db, ws, ci_id, master["path"])
            if decoded:
                part_links_list = {"partLinks": decoded}
                full_id = decoded[-1].get("fullId", "")
                parts = full_id.rsplit("/", 2) if full_id else []
                if len(parts) == 3:
                    last_pn = parts[1]
                    last_pv = parts[2]
        except Exception:
            pass

        if last_pn and last_pv:
            # 用 WIP 策略取最新 iteration（对标 parse_config_spec_str("pi-...") → WIPPSFilter）
            it_row = db.execute(text(
                "SELECT MAX(pi.iteration) FROM partiteration pi "
                "JOIN partrevision pr ON pr.workspace_id=pi.workspace_id "
                "AND pr.partmaster_partnumber=pi.partmaster_partnumber "
                "AND pr.version=pi.partrevision_version "
                "WHERE pi.workspace_id=:ws AND pi.partmaster_partnumber=:pn "
                "AND pi.partrevision_version=:pv"
            ), {"ws": ws, "pn": last_pn, "pv": last_pv}).first()
            last_iteration = it_row[0] if it_row else None

            if last_iteration:
                attr_rows = db.execute(text(
                    "SELECT ia.id, ia.name, ia.mandatory, ia.locked, ia.booleanvalue, "
                    "ia.datevalue, ia.indexvalue, ia.numbervalue, ia.textvalue, "
                    "ia.longtextvalue, ia.urlvalue "
                    "FROM instanceattribute ia "
                    "JOIN partiteration_attribute pia ON pia.instanceattribute_id = ia.id "
                    "WHERE pia.workspace_id=:ws AND pia.partmaster_partnumber=:pn "
                    "AND pia.partrevision_version=:pv AND pia.iteration=:it "
                    "ORDER BY pia.attribute_order"
                ), {"ws": ws, "pn": last_pn, "pv": last_pv,
                    "it": last_iteration}).fetchall()
                part_attrs = [{
                    "id": r[0], "name": r[1], "mandatory": r[2], "locked": r[3],
                    "booleanValue": r[4],
                    "dateValue": str(r[5]) if r[5] else None,
                    "indexValue": r[6], "numberValue": r[7],
                    "textValue": r[8], "longTextValue": r[9], "urlValue": r[10],
                } for r in attr_rows]

                tmpl_rows = db.execute(text(
                    "SELECT iat.id, iat.name, iat.mandatory, iat.locked, iat.dtype, "
                    "iat.attributetype, iat.lov_name, iat.lov_workspace_id "
                    "FROM instanceattributetemplate iat "
                    "JOIN partiteration_pathdata_attr pipa "
                    "  ON pipa.instanceattribute_template_id = iat.id "
                    "WHERE pipa.workspace_id=:ws AND pipa.partmaster_partnumber=:pn "
                    "AND pipa.partrevision_version=:pv AND pipa.iteration=:it "
                    "ORDER BY pipa.attribute_order"
                ), {"ws": ws, "pn": last_pn, "pv": last_pv,
                    "it": last_iteration}).fetchall()
                part_attr_templates = [{
                    "id": r[0], "name": r[1], "mandatory": r[2], "locked": r[3],
                    "typeName": r[4], "attributeType": r[5],
                    "lovName": r[6], "lovWorkspaceId": r[7],
                } for r in tmpl_rows]

        return {
            "id": master_id,
            "path": master["path"],
            "serialNumber": sn,
            "partLinksList": part_links_list,
            "pathDataIterations": iterations,
            "partAttributes": part_attrs,
            "partAttributeTemplates": part_attr_templates,
        }

    def _iter_row_to_dict(self, row) -> dict:
        """将 DB 行转换为迭代 dict。"""
        return {
            "iteration": row[0],
            "pathdatamaster_id": row[1],
            "dateiteration": row[2],
            "iterationNote": row[3],
        }

    def _attr_row_to_dict(self, row) -> dict:
        """将 instanceattribute DB 行转换为 InstanceAttributeDTO dict。"""
        return {
            "id": row[0],
            "name": row[1],
            "mandatory": row[2],
            "locked": row[3],
            "booleanValue": row[4],
            "dateValue": str(row[5]) if row[5] else None,
            "indexValue": row[6],
            "numberValue": row[7],
            "textValue": row[8],
            "longTextValue": row[9],
            "urlValue": row[10],
        }


path_data_service = PathDataService()
