"""工作区管理——对标 Payara WorkspaceManagerBean。

管理工作区（Workspace）的创建、删除、配置。
"""
from sqlalchemy.orm import Session
from sqlalchemy import text


def _normalize_column(col: str) -> str:
    """确保零件列名带 pr. 前缀（对齐 JS cellsFactory 的 key 格式）。"""
    if col.startswith("pr.") or col.startswith("attr"):
        return col
    return f"pr.{col}"


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

    def get_workspace_front_options(self, db: Session, ws: str) -> dict:
        """读取 workspacefrontoptions + 列配置（对齐 Payara getWorkspaceFrontOptions）。"""
        part_cols = db.execute(text(
            "SELECT tablecolumn FROM workspace_parttablecolumn "
            "WHERE workspace_id = :ws ORDER BY partcolumn_order"
        ), {"ws": ws}).fetchall()
        doc_cols = db.execute(text(
            "SELECT tablecolumn FROM workspace_documenttablecolumn "
            "WHERE workspace_id = :ws ORDER BY documentcolumn_order"
        ), {"ws": ws}).fetchall()
        return {
            "documentTableColumns": [r[0] for r in doc_cols],
            "partTableColumns": [_normalize_column(r[0]) for r in part_cols],
        }

    def update_workspace_front_options(self, db: Session, ws: str,
                                        options: dict) -> dict:
        """写入 workspacefrontoptions + 列配置（对齐 Payara updateWorkspaceFrontOptions）。"""
        existing = db.execute(text(
            "SELECT workspace_id FROM workspacefrontoptions WHERE workspace_id = :ws"
        ), {"ws": ws}).fetchone()
        if not existing:
            db.execute(text(
                "INSERT INTO workspacefrontoptions (workspace_id) VALUES (:ws)"
            ), {"ws": ws})
        db.execute(text(
            "DELETE FROM workspace_parttablecolumn WHERE workspace_id = :ws"
        ), {"ws": ws})
        db.execute(text(
            "DELETE FROM workspace_documenttablecolumn WHERE workspace_id = :ws"
        ), {"ws": ws})
        for i, col in enumerate(options.get("partTableColumns", [])):
            db.execute(text(
                "INSERT INTO workspace_parttablecolumn (workspace_id, tablecolumn, partcolumn_order) "
                "VALUES (:ws, :col, :ord)"
            ), {"ws": ws, "col": _normalize_column(col), "ord": i})
        for i, col in enumerate(options.get("documentTableColumns", [])):
            db.execute(text(
                "INSERT INTO workspace_documenttablecolumn (workspace_id, tablecolumn, documentcolumn_order) "
                "VALUES (:ws, :col, :ord)"
            ), {"ws": ws, "col": col, "ord": i})
        db.commit()
        return self.get_workspace_front_options(db, ws)

    def get_workspace_back_options(self, db: Session, ws: str) -> dict:
        """读取 workspacebackoptions.sendemails。"""
        row = db.execute(text(
            "SELECT sendemails FROM workspacebackoptions WHERE workspace_id = :ws"
        ), {"ws": ws}).fetchone()
        return {"workspaceId": ws, "sendEmails": bool(row[0]) if row else False}

    def update_workspace_back_options(self, db: Session, ws: str,
                                       options: dict) -> dict:
        """写入 workspacebackoptions.sendemails。"""
        send_emails = options.get("sendEmails", False)
        existing = db.execute(text(
            "SELECT workspace_id FROM workspacebackoptions WHERE workspace_id = :ws"
        ), {"ws": ws}).fetchone()
        if existing:
            db.execute(text(
                "UPDATE workspacebackoptions SET sendemails = :se WHERE workspace_id = :ws"
            ), {"se": send_emails, "ws": ws})
        else:
            db.execute(text(
                "INSERT INTO workspacebackoptions (workspace_id, sendemails) VALUES (:ws, :se)"
            ), {"ws": ws, "se": send_emails})
        db.commit()
        return self.get_workspace_back_options(db, ws)


workspace_service = WorkspaceService()
