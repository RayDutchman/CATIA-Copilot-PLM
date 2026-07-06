"""RoleManager——用户/用户组删除时清理工作流角色映射。

对齐 Java RoleManager（CDI @Observes @Removed events）。
"""
from sqlalchemy.orm import Session


class RoleManager:
    """工作流角色管理器。"""

    def on_remove_user(self, db: Session, ws: str, user_login: str):
        """用户删除时从所有工作流角色中移除。"""
        from sqlalchemy import text
        db.execute(text(
            "DELETE FROM role_user WHERE user_login = :l "
            "AND user_workspace_id = :ws"
        ), {"l": user_login, "ws": ws})
        db.commit()

    def on_remove_user_group(self, db: Session, ws: str, group_name: str):
        """用户组删除时从所有工作流角色中移除。"""
        from sqlalchemy import text
        db.execute(text(
            "DELETE FROM role_usergroup WHERE usergroup_id = :g"
        ), {"g": group_name})
        db.commit()


role_manager = RoleManager()
