"""UserFolderManager——用户删除时清理 home 文件夹。

对齐 Java UserFolderManager（CDI @Observes @Removed UserEvent）。
"""
from sqlalchemy.orm import Session


class UserFolderManager:
    """用户删除时删除其 home 文件夹。"""

    def on_user_removed(self, db: Session, ws: str, user_login: str):
        """对应用户删除事件，删除用户文件夹。"""
        from sqlalchemy import text
        folder_id = f"{ws}/~{user_login}"
        db.execute(text("DELETE FROM folder WHERE id = :fid"), {"fid": folder_id})
        db.commit()


user_folder_manager = UserFolderManager()
