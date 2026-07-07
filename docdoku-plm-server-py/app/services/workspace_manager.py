"""工作区管理——对标 Payara WorkspaceManagerBean。

管理工作区（Workspace）的创建、删除、配置。
"""
from sqlalchemy.orm import Session
from sqlalchemy import text


class WorkspaceService:
    """工作区管理服务。"""

    def get_workspace(self, db: Session, ws: str) -> dict:
        row = db.execute(text(
            "SELECT * FROM workspace WHERE id = :ws"
        ), {"ws": ws}).first()
        if not row:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("WorkspaceNotFoundException", ws)
        return dict(row._mapping)

    def create_workspace(self, db: Session, ws_id: str,
                          admin_login: str, description: str = "",
                          folder_locked: bool = False) -> dict:
        existing = db.execute(text(
            "SELECT 1 FROM workspace WHERE id = :id"
        ), {"id": ws_id}).first()
        if existing:
            from app.core.exceptions import EntityAlreadyExistsException
            raise EntityAlreadyExistsException("WorkspaceAlreadyExistsException", ws_id)

        db.execute(text(
            "INSERT INTO workspace (id, admin_login, description, folderlocked, enabled) "
            "VALUES (:id, :al, :d, :fl, true)"
        ), {"id": ws_id, "al": admin_login, "d": description, "fl": folder_locked})
        db.commit()

        # 创建 ES 索引
        try:
            from app.services.indexer_manager import indexer_manager
            indexer_manager.create_index(ws_id)
        except Exception:
            pass

        return {"id": ws_id, "adminLogin": admin_login,
                "description": description, "folderLocked": folder_locked,
                "enabled": True}

    def delete_workspace(self, db: Session, ws: str) -> None:
        # 删除 ES 索引
        try:
            from app.services.indexer_manager import indexer_manager
            indexer_manager.delete_index(ws)
        except Exception:
            pass

        db.execute(text("DELETE FROM workspace WHERE id = :id"), {"id": ws})
        db.commit()

    def update_workspace(self, db: Session, ws: str,
                          description: str = None,
                          folder_locked: bool = None) -> dict:
        updates = {}
        if description is not None:
            updates["description"] = description
        if folder_locked is not None:
            updates["folderlocked"] = folder_locked
        if updates:
            set_clause = ", ".join(f"{k} = :{k}" for k in updates)
            db.execute(text(f"UPDATE workspace SET {set_clause} WHERE id = :ws"),
                       {"ws": ws, **updates})
            db.commit()
        return self.get_workspace(db, ws)

    def enable_workspace(self, db: Session, ws: str, enabled: bool) -> dict:
        db.execute(text(
            "UPDATE workspace SET enabled = :e WHERE id = :ws"
        ), {"e": enabled, "ws": ws})
        db.commit()
        return self.get_workspace(db, ws)

    def change_admin(self, db: Session, ws: str, login: str) -> dict:
        db.execute(text(
            "UPDATE workspace SET admin_login = :l WHERE id = :ws"
        ), {"l": login, "ws": ws})
        db.commit()
        return self.get_workspace(db, ws)

    def get_disk_usage(self, db: Session, ws: str) -> int:
        """获取工作区磁盘用量（估算）。"""
        # TODO: 实现基于 vault 的实际磁盘计算
        return 0

    def get_workspace_front_options(self, db: Session, ws: str) -> dict:
        # TODO: 从 workspacefrontoptions 表读取
        return {"workspaceId": ws}

    def update_workspace_front_options(self, db: Session, ws: str,
                                        options: dict) -> dict:
        # TODO: 写入 workspacefrontoptions 表
        return {"workspaceId": ws}

    def get_workspace_back_options(self, db: Session, ws: str) -> dict:
        # TODO: 从 workspacebackoptions 表读取
        return {"workspaceId": ws}

    def update_workspace_back_options(self, db: Session, ws: str,
                                       options: dict) -> dict:
        # TODO: 写入 workspacebackoptions 表
        return {"workspaceId": ws}


workspace_service = WorkspaceService()
