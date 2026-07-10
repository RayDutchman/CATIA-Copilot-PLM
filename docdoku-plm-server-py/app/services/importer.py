"""导入管理——对标 Payara ImporterBean。

处理 Excel/BOM 等批量导入的编排层：
- import_into_parts: 解析 excel → per-part 权限/签出检查 → 属性合并 → dtype-aware 写入
- dry_run_import_into_parts: 预览哪些零件将被 checkout
- import_into_path_data / import_bom / dry_run_import_bom: stub（未实现）
"""
from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.exceptions import NotAllowedException, AccessRightException
from app.services.factory.acl_factory import check_write_access
from app.services.product_manager import ProductService
from app.models.product.part_master import PartMaster
from app.services.importers.attributes_importer_utils import (
    TOKEN_TO_DTYPE as _TOKEN_TO_DTYPE,
    TOKEN_TO_VALUECOL as _TOKEN_TO_VALUECOL,
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
        data = open(file_path, "rb").read()
        result = parse_excel(data, "parts")
        errors = list(result.errors)
        warnings = list(result.warnings)

        svc = ProductService()
        to_write = []            # [(number, version, merged)]
        auto_checked_out = []    # [(number, version)] 本次自动 checkout 的

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

        # 4) 写入库
        for number, version, merged in to_write:
            pm = db.query(PartMaster).filter(
                PartMaster.workspace_id == ws,
                PartMaster.number == number,
            ).one()
            pr = pm.last_revision

            did_checkout = False
            if auto_checkout and not pr.checkout_user_login:
                try:
                    svc.checkout(db, ws, number, version, user_login)
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
                db.commit()

            if auto_checkin and did_checkout and pr.checkout_user_login == user_login:
                try:
                    svc.checkin(db, ws, number, version, user_login)
                except NotAllowedException as e:
                    warnings.append(f"CheckinFailed: {number}: {e}")

        return {"succeed": True, "errors": [], "warnings": warnings}

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

        data = open(file_path, "rb").read()
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
        """批量导入路径数据（暂未实现）。"""
        return {
            "succeed": False,
            "errors": ["NotSupported: import_into_path_data import not implemented"],
            "warnings": [],
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
            "errors": ["NotSupported: dry_run_import_bom import not implemented"],
            "warnings": [],
        }


importer_service = ImporterService()
