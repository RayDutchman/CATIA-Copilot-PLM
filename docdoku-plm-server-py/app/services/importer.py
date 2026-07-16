"""导入管理——对标 Payara ImporterBean。

处理 Excel/BOM 等批量导入的编排层：
- import_into_parts: 解析 excel → per-part 权限/签出检查 → 属性合并 → dtype-aware 写入
- import_into_path_data: 解析 excel → Phase1 查实例+属性合并 → Phase2 批量写 PathData
- dry_run_import_into_parts: 预览哪些零件将被 checkout
- import_bom / dry_run_import_bom: stub（未实现）
"""
from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.exceptions import NotAllowedException, AccessRightException
from app.services.factory.acl_factory import check_write_access
from app.services.product_manager import ProductService
from app.models.product.part_master import PartMaster
from app.models.configuration.product_instance_master import ProductInstanceMaster
from app.services.importers.attributes_importer_utils import (
    TOKEN_TO_DTYPE as _TOKEN_TO_DTYPE,
    TOKEN_TO_VALUECOL as _TOKEN_TO_VALUECOL,
    DTYPE_TO_TOKEN,
    MergedAttribute,
    load_existing_attributes, merge_attributes, would_change,
)

# ── 模块私有常量 ────────────────────────────────────────────────────────────

# dtype 映射（属性 token → Java 全类名）
TOKEN_TO_DTYPE = _TOKEN_TO_DTYPE

# 值列映射（属性 token → instanceattribute 表的值列名）
TOKEN_TO_VALUECOL = _TOKEN_TO_VALUECOL

# 值列白名单（防 SQL 注入：动态列名必须在此集合中）
_VALUECOL_WHITELIST = set(_TOKEN_TO_VALUECOL.values())


# ── dtype-aware 属性写入器 ─────────────────────────────────────────────────

def _write_iteration_attributes(db, ws, pn, ver, iteration, merged):
    """用带 dtype 的原生 SQL 全量替换某迭代的实例属性。调用方负责 commit。

    与 product_manager._sync_instance_attributes 的关键差异：
    后者为所有类型写相同的值列集合但**不写 dtype 列**（依赖 Java 端
    EclipseLink @DiscriminatorColumn 推断），导致查询引擎无法通过 dtype
    区分属性子类。本函数显式写入 dtype，对齐 Payara 实际行为。
    """
    # 1) 查旧属性 ID
    old_rows = db.execute(text(
        "SELECT instanceattribute_id FROM partiteration_attribute "
        "WHERE workspace_id=:ws AND partmaster_partnumber=:pn "
        "AND partrevision_version=:ver AND iteration=:it"
    ), {"ws": ws, "pn": pn, "ver": ver, "it": iteration}).fetchall()
    old_ids = [row[0] for row in old_rows]

    # 2) 删旧关联 + 孤儿 instanceattribute
    db.execute(text(
        "DELETE FROM partiteration_attribute "
        "WHERE workspace_id=:ws AND partmaster_partnumber=:pn "
        "AND partrevision_version=:ver AND iteration=:it"
    ), {"ws": ws, "pn": pn, "ver": ver, "it": iteration})
    for oid in old_ids:
        db.execute(text("DELETE FROM instanceattribute WHERE id=:id"), {"id": oid})

    # 3) 逐条插入新属性
    for order, attr in enumerate(merged):
        dtype = TOKEN_TO_DTYPE.get(attr.type, "InstanceTextAttribute")
        valcol = TOKEN_TO_VALUECOL.get(attr.type, "textvalue")
        # 安全校验：动态列名必须在白名单中
        if valcol not in _VALUECOL_WHITELIST:
            valcol = "textvalue"

        result = db.execute(text(
            f"INSERT INTO instanceattribute "
            f"(dtype, name, mandatory, locked, {valcol}) "
            f"VALUES (:dtype, :name, :mand, :locked, :value) RETURNING id"
        ), {
            "dtype": dtype,
            "name": attr.name,
            "mand": attr.mandatory,
            "locked": attr.locked,
            "value": attr.value,
        })
        attr_id = result.fetchone()[0]
        db.execute(text(
            "INSERT INTO partiteration_attribute "
            "(workspace_id, partmaster_partnumber, partrevision_version, "
            "iteration, instanceattribute_id, attribute_order) "
            "VALUES (:ws, :pn, :ver, :it, :aid, :order)"
        ), {
            "ws": ws, "pn": pn, "ver": ver, "it": iteration,
            "aid": attr_id, "order": order,
        })


def _merged_attrs_to_dicts(attrs: list) -> list[dict]:
    """将 MergedAttribute 列表转为 path_data_service 期望的 dict 格式。"""
    result: list[dict] = []
    for a in attrs:
        d = {
            "name": a.name,
            "mandatory": a.mandatory,
            "locked": a.locked,
            "dtype": TOKEN_TO_DTYPE.get(a.type, "InstanceTextAttribute"),
        }
        if a.type == "BOOLEAN":
            d["booleanValue"] = a.value
        elif a.type == "DATE":
            d["dateValue"] = a.value
        elif a.type == "LOV":
            d["indexValue"] = a.value
        elif a.type == "NUMBER":
            d["numberValue"] = a.value
        elif a.type == "LONG_TEXT":
            d["longTextValue"] = str(a.value) if a.value is not None else None
        else:  # TEXT, URL
            d["textValue"] = str(a.value) if a.value is not None else None
        result.append(d)
    return result


def _freeze_path_data(pds, db, ws: str, ci_id: str, sn: str, master_id: int):
    """auto_freeze：用当前最后迭代属性追加一个新迭代（快照冻结）。

    对齐 Java bulkPathDataUpdate 中 autoFreeze 分支：
    productInstanceManager.addNewPathDataIteration(
        ..., cloneAttributes(pathDataMaster.getLastIteration().getInstanceAttributes()),
        null, null, null)
    """
    max_it = db.execute(text(
        "SELECT MAX(iteration) FROM pathdataiteration "
        "WHERE pathdatamaster_id=:mid"
    ), {"mid": master_id}).first()
    last_iter = max_it[0] if max_it and max_it[0] else 1

    frozen_attrs = pds.get_attributes_for_iteration(db, master_id, last_iter)
    pds.add_new_path_data_iteration(
        db, ws, ci_id, sn, master_id,
        frozen_attrs, None,
    )


# ── 服务类 ─────────────────────────────────────────────────────────────────

class ImporterService:
    """批量导入服务。"""

    def import_into_parts(
        self, db: Session, ws: str, file_path: str,
        original_filename: str, user_login: str, is_admin: bool = False,
        revision_note: str = "",
        auto_checkout: bool = False, auto_checkin: bool = False,
        permissive_update: bool = False,
    ) -> dict:
        """批量导入零件属性数据，对齐 Payara ImporterBean.doPartImport。

        编排流程：
        1. 解析 excel
        2. 逐零件做权限/签出检查 → 属性合并
        3. 有错误则返回 succeed=False（不写库）
        4. 无错误则逐零件 checkout（如需）→ 写入 → checkin（如需）
        """
        from app.services.importers.excel_parser import parse_excel

        # 1) 解析 excel
        with open(file_path, "rb") as f:
            data = f.read()
        result = parse_excel(data, "parts")
        errors = list(result.errors)
        warnings = list(result.warnings)

        svc = ProductService()
        to_write = []            # [(number, version, merged)]

        for part in result.parts:
            pm = db.query(PartMaster).filter(
                PartMaster.workspace_id == ws,
                PartMaster.number == part.number,
            ).one_or_none()

            if pm is None or not pm.revisions:
                errors.append(f"PartMasterNotFound: {part.number}")
                continue

            pr = pm.last_revision
            version = pr.version

            # 检查写权限
            try:
                has_access = check_write_access(
                    db, pr.acl_id, user_login, is_admin, workspace_id=ws,
                )
            except Exception:
                has_access = False

            checked_out = bool(pr.checkout_user_login)
            can_change = (
                (auto_checkout and not checked_out)
                or (checked_out and pr.checkout_user_login == user_login)
            )

            if part.attributes and has_access and can_change:
                last_it = pr.last_iteration_number
                existing = load_existing_attributes(
                    db, ws, part.number, version, last_it,
                )
                merged = merge_attributes(
                    db, ws, existing, part.attributes, part.number, errors,
                )
                to_write.append((part.number, version, merged))
            else:
                # 告警/错误分支（对齐 Java ImporterBean）
                if permissive_update and not has_access:
                    warnings.append(f"NotAccess: {part.number}")
                elif checked_out and pr.checkout_user_login != user_login:
                    msg = f"AlreadyCheckedOut: {part.number} by {pr.checkout_user_login}"
                    (warnings if permissive_update else errors).append(msg)
                elif not checked_out and not auto_checkout:
                    msg = f"NotCheckedOut: {part.number}"
                    (warnings if permissive_update else errors).append(msg)
                elif not has_access:
                    errors.append(f"NotAccess: {part.number}")

        # 有任何错误就不写库
        if errors:
            return {"succeed": False, "errors": errors, "warnings": warnings}

        # 4) 写入库（整体事务：对齐 Java bulkPartUpdate @TransactionAttribute(REQUIRED)）
        # checkout/checkin 使用 auto_commit=False，由本方法统一 commit/rollback
        for number, version, merged in to_write:
            pm = db.query(PartMaster).filter(
                PartMaster.workspace_id == ws,
                PartMaster.number == number,
            ).one()
            pr = pm.last_revision

            did_checkout = False
            if auto_checkout and not pr.checkout_user_login:
                try:
                    svc.checkout(db, ws, number, version, user_login,
                                 auto_commit=False)
                    did_checkout = True
                except Exception as e:
                    errors.append(f"CheckoutFailed: {number}: {e}")
                    continue

            # 重新取 last iteration（checkout 会新建迭代）
            db.refresh(pr)
            target_it = pr.last_iteration_number

            if pr.checkout_user_login == user_login:
                _write_iteration_attributes(
                    db, ws, number, version, target_it, merged,
                )
                if revision_note:
                    db.execute(text(
                        "UPDATE partiteration SET iterationnote=:n "
                        "WHERE workspace_id=:ws AND partmaster_partnumber=:pn "
                        "AND partrevision_version=:ver AND iteration=:it"
                    ), {"n": revision_note, "ws": ws, "pn": number, "ver": version, "it": target_it})
                # flush 确保同会话内后续操作可见（commit 统一在循环外）
                db.flush()

            if auto_checkin and did_checkout and pr.checkout_user_login == user_login:
                try:
                    svc.checkin(db, ws, number, version, user_login,
                                auto_commit=False)
                except NotAllowedException as e:
                    warnings.append(f"CheckinFailed: {number}: {e}")

        # 整体提交或回滚（对齐 Java：任一失败则整体 rollback）
        if errors:
            db.rollback()
        else:
            db.commit()

        return {"succeed": len(errors) == 0, "errors": errors, "warnings": warnings}

    def dry_run_import_into_parts(
        self, db: Session, ws: str, file_path: str,
        original_filename: str, user_login: str, is_admin: bool = False,
        auto_checkout: bool = False, auto_checkin: bool = False,
        permissive_update: bool = False,
    ) -> dict:
        """试运行批量导入——返回需要 checkout 的零件列表（不写库）。

        对齐 Payara ImporterBean.dryRunImportIntoParts 语义。
        """
        from app.services.importers.excel_parser import parse_excel

        with open(file_path, "rb") as f:
            data = f.read()
        result = parse_excel(data, "parts")

        to_checkout = []

        for part in result.parts:
            pm = db.query(PartMaster).filter(
                PartMaster.workspace_id == ws,
                PartMaster.number == part.number,
            ).one_or_none()

            if pm is None or not pm.revisions:
                continue

            pr = pm.last_revision
            version = pr.version
            checked_out = bool(pr.checkout_user_login)

            try:
                has_access = check_write_access(
                    db, pr.acl_id, user_login, is_admin, workspace_id=ws,
                )
            except Exception:
                has_access = False

            if auto_checkout and not checked_out and has_access and part.attributes:
                existing = load_existing_attributes(
                    db, ws, part.number, version, pr.last_iteration_number,
                )
                if would_change(db, ws, existing, part.attributes):
                    to_checkout.append({
                        "workspaceId": ws,
                        "partNumber": part.number,
                        "version": version,
                    })

        return {"partRevsToCheckout": to_checkout, "partsToCreate": []}

    def import_into_path_data(
        self, db: Session, ws: str, file_path: str,
        original_filename: str, user_login: str = "", is_admin: bool = False,
        revision_note: str = "",
        auto_freeze: bool = False,
        permissive_update: bool = False,
    ) -> dict:
        """批量导入路径数据，对齐 Payara ImporterBean.doPathDataImport。

        编排流程：
        1. 解析 excel（pathdata 模式：前三列 ctx.productId/ctx.serialNumber/pm.number）
        2. Phase 1（createOrUpdatePathData）：逐行查产物实例→查/建 PathDataMaster→属性合并
        3. Phase 2（bulkPathDataUpdate）：逐行写 PathDataMaster/Iteration + auto_freeze
        """
        from app.services.importers.excel_parser import parse_excel
        from app.services.products.path_data_service import path_data_service

        # 1) 解析 excel
        with open(file_path, "rb") as f:
            data = f.read()
        result = parse_excel(data, "pathdata")
        errors = list(result.errors)
        warnings = list(result.warnings)

        pds = path_data_service

        # 2) Phase 1: createOrUpdatePathData —— 逐行验证 + 属性合并
        to_write: list[tuple] = []  # (ci_id, sn, path, merged_attrs, note, existing_master_id|None)

        for row in result.parts:
            ci_id = row.product_id
            sn = row.serial_number
            pd_path = row.number  # 第三列 pm.number = 路径标识

            if not ci_id or not sn:
                errors.append(
                    f"MissingPathDataContext: path='{pd_path}' "
                    f"missing productId or serialNumber"
                )
                continue

            # 检查产物实例是否存在
            inst_iter = db.execute(text(
                "SELECT iteration FROM productinstanceiteration "
                "WHERE workspace_id=:ws AND configurationitem_id=:ci "
                "  AND prdinstancemaster_serialnumber=:sn "
                "ORDER BY iteration DESC LIMIT 1"
            ), {"ws": ws, "ci": ci_id, "sn": sn}).first()

            if not inst_iter:
                errors.append(f"ProductInstanceMasterNotFound: {ci_id}/{sn}")
                continue

            # 实例级写权限检查（对齐 Java productInstanceManager.canWrite + checkProductInstanceWriteAccess）
            # ProductInstanceManagerBean.java:909-918, 1230-1244
            prod_inst_master = db.query(ProductInstanceMaster).filter(
                ProductInstanceMaster.workspace_id == ws,
                ProductInstanceMaster.configurationitem_id == ci_id,
                ProductInstanceMaster.serialnumber == sn,
            ).one_or_none()

            if prod_inst_master is None:
                errors.append(f"ProductInstanceMasterNotFound: {ci_id}/{sn}")
                continue

            try:
                check_write_access(db, prod_inst_master.acl_id, user_login, is_admin, workspace_id=ws)
            except AccessRightException as e:
                errors.append(f"AccessRightException: {ci_id}/{sn}: {e}")
                continue

            # 查找已存在的 PathDataMaster
            existing_master = pds.get_path_data_by_path(db, ws, ci_id, sn, pd_path)

            if existing_master:
                # ── 已存在 PathDataMaster → 加载最后迭代属性，合并 ──
                master_id = existing_master["id"]
                max_it_row = db.execute(text(
                    "SELECT MAX(iteration) FROM pathdataiteration "
                    "WHERE pathdatamaster_id=:mid"
                ), {"mid": master_id}).first()
                last_iter = max_it_row[0] if max_it_row and max_it_row[0] else 1

                existing_rows = db.execute(text(
                    "SELECT ia.dtype, ia.name, ia.mandatory, ia.locked, "
                    "ia.textvalue, ia.longtextvalue, ia.numbervalue, ia.datevalue, "
                    "ia.booleanvalue, ia.urlvalue, ia.indexvalue "
                    "FROM pathdataiteration_attribute pdia "
                    "JOIN instanceattribute ia ON ia.id = pdia.instanceattribute_id "
                    "WHERE pdia.pathdatamaster_id=:mid "
                    "  AND pdia.pathdata_iteration=:it "
                    "ORDER BY pdia.attribute_order"
                ), {"mid": master_id, "it": last_iter}).fetchall()

                existing_attrs: list[MergedAttribute] = []
                for erow in existing_rows:
                    dtype = erow.dtype or "InstanceTextAttribute"
                    token = DTYPE_TO_TOKEN.get(dtype, "TEXT")
                    col = TOKEN_TO_VALUECOL.get(token, "textvalue")
                    value = getattr(erow, col, None) if hasattr(erow, col) else None
                    existing_attrs.append(MergedAttribute(
                        name=erow.name, type=token, value=value,
                        mandatory=bool(erow.mandatory), locked=bool(erow.locked),
                    ))

                merged = merge_attributes(
                    db, ws, existing_attrs, row.attributes, pd_path, errors,
                )
                to_write.append((ci_id, sn, pd_path, merged, revision_note, master_id))
            else:
                # ── 新建 PathDataMaster —— 从空列表合并（触发新建模式） ──
                merged = merge_attributes(
                    db, ws, [], row.attributes, pd_path, errors,
                )
                to_write.append((ci_id, sn, pd_path, merged, revision_note, None))

        # 有任何错误就不写库（对齐 Java：errors.size()>0 → 直接返回）
        if errors:
            return {"succeed": False, "errors": errors, "warnings": warnings}

        # 3) Phase 2: bulkPathDataUpdate
        for ci_id, sn, pd_path, attrs, note, existing_master_id in to_write:
            try:
                attr_dicts = _merged_attrs_to_dicts(attrs)

                if existing_master_id is not None:
                    # 已有 master → 追加新迭代
                    pds.add_new_path_data_iteration(
                        db, ws, ci_id, sn, existing_master_id,
                        attr_dicts, note,
                        auto_commit=False,
                    )
                    if auto_freeze:
                        _freeze_path_data(pds, db, ws, ci_id, sn, existing_master_id)
                else:
                    # 新建 master + 首迭代
                    pds.create_path_data_master(
                        db, ws, ci_id, sn, pd_path,
                        attr_dicts, note,
                        auto_commit=False,
                    )
                    if auto_freeze:
                        new_master = pds.get_path_data_by_path(db, ws, ci_id, sn, pd_path)
                        if new_master:
                            _freeze_path_data(pds, db, ws, ci_id, sn, new_master["id"])
            except Exception as e:
                msg = f"PathDataUpdateFailed: {ci_id}/{sn}/{pd_path}: {e}"
                if permissive_update:
                    warnings.append(msg)
                else:
                    errors.append(msg)

        if errors:
            db.rollback()
        else:
            db.commit()

        return {
            "succeed": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def import_bom(
        self, db: Session, ws: str, file_path: str,
        original_filename: str, user_login: str = "", is_admin: bool = False,
        revision_note: str = "",
        auto_checkout: bool = False, auto_checkin: bool = False,
        permissive_update: bool = False,
    ) -> dict:
        """批量导入 BOM 结构（暂未实现，Java 侧亦无此实现）。"""
        return {
            "succeed": False,
            "errors": ["NotSupported: import_bom import not implemented"],
            "warnings": [],
        }

    def dry_run_import_bom(
        self, db: Session, ws: str, file_path: str,
        original_filename: str, user_login: str = "", is_admin: bool = False,
        auto_checkout: bool = False, auto_checkin: bool = False,
        permissive_update: bool = False,
    ) -> dict:
        """试运行 BOM 导入（暂未实现）。"""
        return {
            "succeed": False,
            "errors": ["NotSupported: dry_run_import_bom import not implemented"],
            "warnings": [],
        }

    def dry_run_import_path_data(
        self, db: Session, ws: str, file_path: str,
        original_filename: str, user_login: str = "", is_admin: bool = False,
        permissive_update: bool = False,
    ) -> dict:
        """试运行 PathData 导入——解析 excel 并返回将受影响的路径清单（不写库）。

        对齐 Java ImporterBean.dryRunImportIntoPathData 语义：
        逐行验证 productId/serialNumber → 查实例是否存在 → 返回路径列表。
        """
        from app.services.importers.excel_parser import parse_excel

        with open(file_path, "rb") as f:
            data = f.read()
        result = parse_excel(data, "pathdata")

        to_checkout: list[dict] = []

        for part in result.parts:
            ci_id = part.product_id
            sn = part.serial_number
            pd_path = part.number

            if not ci_id or not sn:
                continue

            inst_iter = db.execute(text(
                "SELECT iteration FROM productinstanceiteration "
                "WHERE workspace_id=:ws AND configurationitem_id=:ci "
                "  AND prdinstancemaster_serialnumber=:sn "
                "ORDER BY iteration DESC LIMIT 1"
            ), {"ws": ws, "ci": ci_id, "sn": sn}).first()

            if not inst_iter:
                continue

            to_checkout.append({
                "workspaceId": ws,
                "partNumber": pd_path,
                "version": "",
            })

        return {"partRevsToCheckout": to_checkout, "partsToCreate": []}


importer_service = ImporterService()
