"""PartNotificationManager——零件事件 → 通知处理。

对齐 Java PartNotificationManager（CDI @Observes @Removed/@CheckedIn PartIterationEvent）。
"""
from sqlalchemy.orm import Session


class PartNotificationManager:
    """零件事件通知管理器。"""

    def on_remove_part_iteration(self, db: Session, ws: str,
                                  part_number: str, version: str, iteration: int):
        """零件迭代删除时清理关联通知。"""
        from sqlalchemy import text
        db.execute(text(
            "DELETE FROM modificationnotification WHERE impacted_workspace_id = :ws "
            "AND impacted_partmaster_partnumber = :pn "
            "AND impacted_partrevision_version = :ver "
            "AND impacted_iteration = :iter"
        ), {"ws": ws, "pn": part_number, "ver": version, "iter": iteration})
        db.commit()

    def on_remove_part_revision(self, db: Session, ws: str,
                                 part_number: str, version: str):
        """零件修订版删除时清理关联通知。"""
        from sqlalchemy import text
        db.execute(text(
            "DELETE FROM modificationnotification WHERE impacted_workspace_id = :ws "
            "AND impacted_partmaster_partnumber = :pn "
            "AND impacted_partrevision_version = :ver"
        ), {"ws": ws, "pn": part_number, "ver": version})
        db.commit()

    def on_check_in_part_iteration(self, db: Session, ws: str,
                                    part_number: str, version: str, iteration: int):
        """零件迭代检入时触发通知。"""
        pass


part_notification_manager = PartNotificationManager()
