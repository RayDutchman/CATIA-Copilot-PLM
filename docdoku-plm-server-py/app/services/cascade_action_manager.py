"""级联操作管理——对标 Payara CascadeActionManagerBean。

处理 checkout/undo_checkout/checkin 级联操作。
"""
from sqlalchemy.orm import Session
from sqlalchemy import text


class CascadeActionService:
    """级联操作服务。遍历组件树，逐级执行操作。"""

    def _traverse_components(self, db: Session, ws: str, pn: str, pv: str) -> list:
        """收集子树所有零件修订（BFS 遍历）。"""
        from app.models.part import PartRevision
        result = []
        seen = {f"{pn}-{pv}"}
        queue = [(ws, pn, pv)]
        while queue:
            c_ws, c_pn, c_pv = queue.pop(0)
            pr = db.query(PartRevision).filter(
                PartRevision.workspace_id == c_ws,
                PartRevision.partmaster_partnumber == c_pn,
                PartRevision.version == c_pv,
            ).first()
            if not pr:
                continue
            result.append(pr)
            last_it = pr.last_iteration
            if last_it:
                rows = db.execute(text(
                    "SELECT DISTINCT pul.component_partnumber, "
                    "pul.component_workspace_id, pr2.version "
                    "FROM partusagelink pul "
                    "JOIN part_iteration_usagelink piul ON piul.component_id = pul.id "
                    "JOIN partrevision pr2 ON pr2.partmaster_partnumber = pul.component_partnumber "
                    "  AND pr2.workspace_id = pul.component_workspace_id "
                    "WHERE piul.workspace_id = :ws "
                    "  AND piul.partmaster_partnumber = :pn "
                    "  AND piul.partrevision_version = :pv "
                    "  AND piul.iteration = :it "
                    "ORDER BY pr2.creationdate DESC"
                ), {"ws": c_ws, "pn": c_pn, "pv": c_pv, "it": last_it.iteration}).fetchall()
                for row in rows:
                    key = f"{row[0]}-{row[2]}"
                    if key not in seen:
                        seen.add(key)
                        queue.append((row[1] or ws, row[0], row[2]))
        return result

    def cascade_check_out(self, db: Session, ws: str, part_number: str,
                          part_version: str, ci_id: str, path: str) -> dict:
        """级联检出：遍历组件树，逐级 checkout 所有未检出节点。"""
        from app.services.product_manager import product_service
        parts = self._traverse_components(db, ws, part_number, part_version)
        checked_out = []
        errors = []
        for pr in parts:
            if not pr.checkout_user_login:
                try:
                    product_service.checkout(db, ws, pr.partmaster_partnumber,
                                             pr.version, "")
                    checked_out.append(pr.partmaster_partnumber)
                except Exception as e:
                    errors.append({"part": f"{pr.partmaster_partnumber}-{pr.version}",
                                   "error": str(e)})
        return {"status": "ok", "checkedOut": checked_out, "errors": errors}

    def cascade_undo_check_out(self, db: Session, ws: str, part_number: str,
                                part_version: str, ci_id: str, path: str) -> dict:
        """级联撤销检出：遍历组件树，逐级撤销。"""
        from app.services.product_manager import product_service
        parts = self._traverse_components(db, ws, part_number, part_version)
        undone = []
        errors = []
        for pr in parts:
            if pr.checkout_user_login:
                try:
                    product_service.undo_checkout(db, ws, pr.partmaster_partnumber,
                                                  pr.version, "")
                    undone.append(pr.partmaster_partnumber)
                except Exception as e:
                    errors.append({"part": f"{pr.partmaster_partnumber}-{pr.version}",
                                   "error": str(e)})
        return {"status": "ok", "undoneCheckout": undone, "errors": errors}

    def cascade_check_in(self, db: Session, ws: str, part_number: str,
                          part_version: str, ci_id: str, path: str,
                          iteration_note: str = "") -> dict:
        """级联检入：遍历组件树，逐级检入。"""
        from app.services.product_manager import product_service
        parts = self._traverse_components(db, ws, part_number, part_version)
        checked_in = []
        errors = []
        for pr in parts:
            if pr.checkout_user_login:
                try:
                    product_service.checkin(db, ws, pr.partmaster_partnumber,
                                            pr.version, "")
                    checked_in.append(pr.partmaster_partnumber)
                except Exception as e:
                    errors.append({"part": f"{pr.partmaster_partnumber}-{pr.version}",
                                   "error": str(e)})
        return {"status": "ok", "checkedIn": checked_in, "errors": errors}


cascade_action_service = CascadeActionService()
