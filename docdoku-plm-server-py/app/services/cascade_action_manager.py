"""级联操作管理——对标 Payara CascadeActionManagerBean。

处理 checkout/undo_checkout/checkin 级联操作。
"""
from sqlalchemy.orm import Session


class CascadeActionService:
    """级联操作服务。委托 product_service 执行底层操作。"""

    def cascade_check_out(self, db: Session, ws: str, part_number: str,
                          part_version: str, ci_id: str, path: str) -> dict:
        """级联检出。"""
        from app.services.product_manager import product_service
        # TODO: 实现完整的级联检CT逻辑（遍历组件树，逐级 checkout）
        return product_service.cascade_op(db, ws, part_number, part_version,
                                           ci_id, path, "checkout")

    def cascade_undo_check_out(self, db: Session, ws: str, part_number: str,
                                part_version: str, ci_id: str, path: str) -> dict:
        """级联撤销检出。"""
        from app.services.product_manager import product_service
        return product_service.cascade_op(db, ws, part_number, part_version,
                                           ci_id, path, "undocheckout")

    def cascade_check_in(self, db: Session, ws: str, part_number: str,
                          part_version: str, ci_id: str, path: str,
                          iteration_note: str = "") -> dict:
        """级联检入。"""
        from app.services.product_manager import product_service
        return product_service.cascade_op(db, ws, part_number, part_version,
                                           ci_id, path, "checkin", iteration_note)


cascade_action_service = CascadeActionService()
