"""工作区管理——对标 Payara WorkspaceManagerBean。

管理工作区（Workspace）的创建、删除、配置。
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.services.workspace_deletion import cascade_delete_workspace


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
                          admin_login: str, current_user_login: str = None,
                          description: str = "",
                          folder_locked: bool = False) -> dict:
        """创建工作区（对齐 Payara WorkspaceManagerBean.createWorkspace）。

        含：ADMIN_VALIDATION 策略校验 + 命名校验 + workspace INSERT +
        createUser(userdata) + addUserMembership(workspaceusermembership) + ES 索引。
        """
        from app.core.exceptions import (
            AccessRightException, NotAllowedException, EntityAlreadyExistsException,
        )
        from app.models.util.naming_convention import is_valid_name

        # 平台策略：ADMIN_VALIDATION(=1) 时仅管理员可创建，且 workspace 默认 disabled
        strategy_row = db.execute(text(
            "SELECT workspacecreationstrategy FROM platformoptions LIMIT 1"
        )).first()
        is_admin_validation = strategy_row is not None and strategy_row[0] == 1
        if is_admin_validation and current_user_login is not None:
            is_admin = db.execute(text(
                "SELECT 1 FROM usergroupmapping WHERE login=:l AND groupname='admin'"
            ), {"l": current_user_login}).first()
            if not is_admin:
                raise AccessRightException("AccessRightException", current_user_login)

        if not ws_id:
            raise NotAllowedException("NotAllowedException9", ws_id)
        # 命名约定校验
        if not is_valid_name(ws_id):
            raise NotAllowedException("NotAllowedException9", ws_id)

        existing = db.execute(text(
            "SELECT id FROM workspace WHERE id = :id"
        ), {"id": ws_id}).first()
        if existing:
            raise EntityAlreadyExistsException("WorkspaceAlreadyExistsException", ws_id)

        enabled = not is_admin_validation  # ADMIN_VALIDATION → false，否则 true

        db.execute(text(
            "INSERT INTO workspace (id, description, enabled, folderlocked, admin_login) "
            "VALUES (:id, :desc, :enabled, :folder_locked, :admin)"
        ), {"id": ws_id, "desc": description, "enabled": enabled,
            "folder_locked": folder_locked, "admin": admin_login})

        # Payara 对齐: createWorkspace → createUser + addUserMembership
        db.execute(text(
            "INSERT INTO userdata (login, workspace_id) VALUES (:login, :ws)"
        ), {"login": admin_login, "ws": ws_id})
        db.execute(text(
            "INSERT INTO workspaceusermembership "
            "(workspace_id, member_login, member_workspace_id) "
            "VALUES (:ws, :login, :ws) "
            "ON CONFLICT DO NOTHING"
        ), {"ws": ws_id, "login": admin_login})
        db.commit()

        # 创建 ES 索引（对标 createWorkspace:157）
        try:
            from app.services.indexer_manager import indexer_manager
            indexer_manager.create_index(ws_id)
        except Exception:
            pass

        return {"id": ws_id, "description": description, "enabled": enabled,
                "folderLocked": folder_locked, "admin": admin_login}

    def delete_workspace(self, db: Session, ws: str) -> None:
        """完整级联删除工作区（对齐 WorkspaceDAO.removeWorkspace）。"""
        cascade_delete_workspace(db, ws)

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

    # ============================================================
    # Admin endpoints
    # ============================================================

    def list_workspaces_admin(self, db: Session) -> list:
        return db.execute(text(
            "SELECT id, description, enabled, folderlocked, admin_login "
            "FROM workspace ORDER BY id"
        )).fetchall()

    def get_workspace_admin(self, db: Session, ws: str):
        row = db.execute(text(
            "SELECT id, description, enabled, folderlocked, admin_login "
            "FROM workspace WHERE id = :id"
        ), {"id": ws}).fetchone()
        if not row:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("WorkspaceNotFoundException", ws)
        return row

    def update_workspace_admin(self, db: Session, ws: str, body: dict):
        existing = db.execute(text(
            "SELECT id FROM workspace WHERE id = :id"
        ), {"id": ws}).fetchone()
        if not existing:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("WorkspaceNotFoundException", ws)

        updates = {}
        if "description" in body:
            updates["description"] = body["description"]
        if "enabled" in body:
            updates["enabled"] = body["enabled"]
        if "folderLocked" in body:
            updates["folderlocked"] = body["folderLocked"]

        if updates:
            set_clause = ", ".join(f"{k} = :{k}" for k in updates)
            db.execute(text(
                f"UPDATE workspace SET {set_clause} WHERE id = :id"
            ), {**updates, "id": ws})
            db.commit()

        return self.get_workspace_admin(db, ws)

    def enable_workspace_admin(self, db: Session, ws: str, enabled: bool):
        existing = db.execute(text(
            "SELECT id FROM workspace WHERE id = :w"
        ), {"w": ws}).fetchone()
        if not existing:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("WorkspaceNotFoundException", ws)
        db.execute(text("UPDATE workspace SET enabled = :e WHERE id = :w"),
                   {"e": enabled, "w": ws})
        db.commit()
        return self.get_workspace_admin(db, ws)

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
