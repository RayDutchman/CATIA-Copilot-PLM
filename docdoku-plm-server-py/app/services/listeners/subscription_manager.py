"""SubscriptionManager——标签/用户/用户组变更 → 订阅通知。

对齐 Java SubscriptionManager（CDI @Observes events）。
"""
from sqlalchemy.orm import Session


class SubscriptionManager:
    """订阅事件管理器。"""

    def on_remove_tag(self, db: Session, ws: str, tag_label: str):
        """标签删除时清理关联订阅（用户 + 用户组，对齐 Java removeAllTagSubscriptions(Tag)）。"""
        from sqlalchemy import text
        db.execute(text(
            "DELETE FROM tagusersubscription WHERE tag_label = :l AND tag_workspace_id = :ws"
        ), {"l": tag_label, "ws": ws})
        db.execute(text(
            "DELETE FROM tagusergroupsubscription WHERE tag_label = :l AND tag_workspace_id = :ws"
        ), {"l": tag_label, "ws": ws})
        db.commit()

    def on_remove_user(self, db: Session, ws: str, user_login: str):
        """用户删除时清理其所有订阅（文档状态/迭代订阅 + 标签订阅）。"""
        from sqlalchemy import text
        db.execute(text(
            "DELETE FROM statechangesubscription WHERE subscriber_login = :l "
            "AND subscriber_workspace_id = :ws"
        ), {"l": user_login, "ws": ws})
        db.execute(text(
            "DELETE FROM iterationchangesubscription WHERE subscriber_login = :l "
            "AND subscriber_workspace_id = :ws"
        ), {"l": user_login, "ws": ws})
        db.execute(text(
            "DELETE FROM tagusersubscription WHERE subscriber_login = :l "
            "AND subscriber_workspace_id = :ws"
        ), {"l": user_login, "ws": ws})
        db.commit()

    def on_remove_user_group(self, db: Session, ws: str, group_name: str):
        """用户组删除时清理关联订阅。"""
        from sqlalchemy import text
        db.execute(text(
            "DELETE FROM tagusergroupsubscription WHERE subscriber_id = :g "
            "AND subscriber_workspace_id = :ws"
        ), {"g": group_name, "ws": ws})
        db.commit()

    def on_tag_item(self, db: Session, ws: str, tag_label: str,
                     part_number: str = None, doc_id: str = None):
        """标签添加到实体时通知订阅者。"""
        pass

    def on_untag_item(self, db: Session, ws: str, tag_label: str,
                       part_number: str = None, doc_id: str = None):
        """标签从实体移除时通知订阅者。"""
        pass


subscription_manager = SubscriptionManager()
