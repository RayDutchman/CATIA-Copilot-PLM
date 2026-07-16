from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.auth import Account
from app.models.common.user_group import UserGroup
from app.core.exceptions import (
    EntityNotFoundException, EntityConstraintException,
    UserAlreadyExistsException, UserGroupAlreadyExistsException,
    UserGroupNotFoundException, UserNotActiveException,
    NotAllowedException,
)


class UserMgmtService:
    def list_users(self, db: Session, ws: str) -> list:
        rows = db.execute(text(
            "SELECT u.login, u.workspace_id, a.name, a.email, a.language "
            "FROM userdata u JOIN account a ON u.login = a.login "
            "WHERE u.workspace_id = :ws"
        ), {"ws": ws}).fetchall()
        return [{"login": r[0], "workspaceId": r[1], "name": r[2],
                 "email": r[3], "language": r[4] or ""}
                for r in rows]

    def who_am_i(self, db: Session, ws: str, login: str) -> dict:
        from app.services.account_manager import account_service
        return account_service.who_am_i(db, ws, login)

    def list_groups(self, db: Session, ws: str) -> list[UserGroup]:
        return db.query(UserGroup).filter(UserGroup.workspace_id == ws).all()

    def create_group(self, db: Session, ws: str, group_id: str) -> UserGroup:
        existing = db.query(UserGroup).filter(
            UserGroup.id == group_id, UserGroup.workspace_id == ws).first()
        if existing:
            raise UserGroupAlreadyExistsException("UserGroupAlreadyExistsException", group_id)
        g = UserGroup(id=group_id, workspace_id=ws)
        db.add(g)
        db.flush()  # 确保 usergroup 行先于 membership 写入，避免 FK 违规
        db.execute(text(
            "INSERT INTO workspaceusergroupmembership "
            "(workspace_id, member_id, member_workspace_id, readonly) "
            "VALUES (:ws, :gid, :ws, false) "
            "ON CONFLICT (workspace_id, member_id, member_workspace_id) DO NOTHING"
        ), {"ws": ws, "gid": group_id})
        db.commit()
        db.refresh(g)
        return g

    def delete_group(self, db: Session, ws: str, group_id: str):
        g = db.query(UserGroup).filter(
            UserGroup.id == group_id, UserGroup.workspace_id == ws).first()
        if not g:
            raise UserGroupNotFoundException("UserGroupNotFoundException", group_id)
        # ACL 约束检查：组被 ACL 引用时禁止删除
        acl_ref = db.execute(text(
            "SELECT 1 FROM aclusergroupentry "
            "WHERE principal_id = :gid AND principal_workspace_id = :ws"
        ), {"gid": group_id, "ws": ws}).first()
        if acl_ref:
            raise EntityConstraintException("EntityConstraintException11")
        # 先删 workspace 级别的组成员关系，再删组本身
        db.execute(text(
            "DELETE FROM workspaceusergroupmembership "
            "WHERE member_id = :gid AND member_workspace_id = :ws"
        ), {"gid": group_id, "ws": ws})
        db.delete(g)
        db.commit()

    def add_user(self, db: Session, ws: str, login: str, group_id: str | None = None):
        acc = db.query(Account).filter(Account.login == login).first()
        if not acc:
            raise EntityNotFoundException("UserNotFoundException", login)
        # 检查是否已在 workspace
        existing = db.execute(text(
            "SELECT COUNT(*) FROM userdata WHERE login = :l AND workspace_id = :w"
        ), {"l": login, "w": ws}).scalar()
        if existing > 0:
            raise UserAlreadyExistsException("UserAlreadyExistsException", login)
        db.execute(text(
            "INSERT INTO userdata (login, workspace_id) VALUES (:l, :w)"
        ), {"l": login, "w": ws})
        # 添加 workspaceusermembership 记录（enable_user 语义）
        db.execute(text(
            "INSERT INTO workspaceusermembership "
            "(workspace_id, member_login, member_workspace_id) "
            "VALUES (:ws, :login, :ws) "
            "ON CONFLICT (workspace_id, member_login, member_workspace_id) DO NOTHING"
        ), {"ws": ws, "login": login})
        if group_id:
            # Payara 对齐：先移除直接 membership，避免双重成员关系
            db.execute(text(
                "DELETE FROM workspaceusermembership "
                "WHERE workspace_id = :ws AND member_login = :login"
            ), {"ws": ws, "login": login})
            db.execute(text(
                "INSERT INTO usergroupmapping (login, groupname) VALUES (:l, :g) "
                "ON CONFLICT DO NOTHING"
            ), {"l": login, "g": group_id})
        db.commit()

    def remove_user_from_workspace(self, db: Session, ws: str, login: str):
        # 先删 workspace 级别的成员关系（避免 FK 约束冲突）
        db.execute(text(
            "DELETE FROM workspaceusermembership "
            "WHERE member_login = :l AND workspace_id = :w"
        ), {"l": login, "w": ws})
        db.execute(text(
            "DELETE FROM workspaceusergroupmembership "
            "WHERE member_id IN (SELECT groupname FROM usergroupmapping WHERE login = :l) "
            "AND workspace_id = :w"
        ), {"l": login, "w": ws})
        db.execute(text(
            "DELETE FROM usergroupmapping "
            "WHERE login = :l AND groupname IN (SELECT id FROM usergroup WHERE workspace_id = :w)"
        ), {"l": login, "w": ws})
        db.execute(text(
            "DELETE FROM userdata WHERE login = :l AND workspace_id = :w"
        ), {"l": login, "w": ws})
        db.commit()

    def check_user_active(self, db: Session, ws: str, login: str) -> bool:
        """检查用户是否在 workspace 中处于激活状态。"""
        row = db.execute(text(
            "SELECT 1 FROM userdata WHERE login = :l AND workspace_id = :w"
        ), {"l": login, "w": ws}).first()
        if not row:
            raise EntityNotFoundException("UserNotFoundException", login)
        membership = db.execute(text(
            "SELECT 1 FROM workspaceusermembership "
            "WHERE workspace_id = :ws AND member_login = :login"
        ), {"ws": ws, "login": login}).first()
        if not membership:
            raise UserNotActiveException("UserNotActiveException", login, ws)
        return True

    def enable_user(self, db: Session, ws: str, login: str):
        db.execute(text(
            "INSERT INTO workspaceusermembership "
            "(workspace_id, member_login, member_workspace_id) "
            "VALUES (:ws, :login, :ws) "
            "ON CONFLICT (workspace_id, member_login, member_workspace_id) DO NOTHING"
        ), {"ws": ws, "login": login})
        db.commit()

    def disable_user(self, db: Session, ws: str, login: str):
        db.execute(text(
            "DELETE FROM workspaceusermembership "
            "WHERE workspace_id = :ws AND member_login = :login"
        ), {"ws": ws, "login": login})
        db.commit()

    def list_memberships(self, db: Session, ws: str) -> list:
        """Payara 对齐：读 workspaceusermembership 表获取 readOnly 状态。"""
        from sqlalchemy import text
        rows = db.execute(text(
            "SELECT u.login, a.name, a.email, a.language, wm.readonly "
            "FROM userdata u "
            "JOIN account a ON u.login = a.login "
            "LEFT JOIN workspaceusermembership wm "
            "  ON wm.member_login = u.login "
            "  AND wm.member_workspace_id = :ws "
            "  AND wm.workspace_id = :ws2 "
            "WHERE u.workspace_id = :ws3"
        ), {"ws": ws, "ws2": ws, "ws3": ws}).fetchall()
        result = []
        for r in rows:
            login = r[0]
            has_membership = r[4] is not None  # NULL = 无显式记录
            read_only = bool(r[4]) if has_membership else True  # 无记录默认 READ_ONLY
            result.append({
                "workspaceId": ws,
                "member": {
                    "login": login, "name": r[1] or "",
                    "email": r[2] or "", "language": r[3] or "",
                    "workspaceId": ws,
                },
                "readOnly": read_only,
            })
        return result

    def create_account(self, db: Session, login: str, password: str,
                       email: str, name: str, language: str,
                       timezone: str = "") -> Account:
        from app.services.account_manager import account_service
        return account_service.create_account(db, login, password, email, name, language,
                                              timezone=timezone)

    def update_account(self, db: Session, login: str, fields: dict) -> Account:
        from app.services.account_manager import account_service
        return account_service.update_account(db, login, fields)

    def list_workspaces_for_user(self, db: Session, login: str) -> list:
        rows = db.execute(text(
            "SELECT w.id, w.enabled, w.description, w.folderlocked FROM workspace w "
            "JOIN userdata u ON w.id = u.workspace_id "
            "WHERE u.login = :l"
        ), {"l": login}).fetchall()
        return [{"id": r[0], "enabled": r[1],
                 "description": r[2] or "", "folderLocked": bool(r[3]) if r[3] is not None else False}
                for r in rows]

    # ============================================================
    # User group helpers (routers/user_groups.py)
    # ============================================================

    def get_users_in_group(self, db: Session, group_id: str) -> list:
        rows = db.execute(text(
            "SELECT a.login, a.name, a.email, a.language "
            "FROM account a "
            "JOIN usergroupmapping m ON a.login = m.login "
            "WHERE m.groupname = :gid"
        ), {"gid": group_id}).fetchall()
        return [{"login": r[0], "name": r[1], "email": r[2], "language": r[3]} for r in rows]

    def enable_group(self, db: Session, ws: str, group_id: str):
        existing = db.execute(text(
            "SELECT id FROM usergroup WHERE id = :gid AND workspace_id = :ws"
        ), {"gid": group_id, "ws": ws}).fetchone()
        if not existing:
            raise UserGroupNotFoundException("UserGroupNotFoundException", group_id)
        db.execute(text(
            "INSERT INTO workspaceusergroupmembership "
            "(workspace_id, member_id, member_workspace_id, readonly) "
            "VALUES (:ws, :gid, :ws, false) "
            "ON CONFLICT (workspace_id, member_id, member_workspace_id) DO NOTHING"
        ), {"ws": ws, "gid": group_id})
        db.commit()

    def disable_group(self, db: Session, ws: str, group_id: str):
        existing = db.execute(text(
            "SELECT id FROM usergroup WHERE id = :gid AND workspace_id = :ws"
        ), {"gid": group_id, "ws": ws}).fetchone()
        if not existing:
            raise UserGroupNotFoundException("UserGroupNotFoundException", group_id)
        db.execute(text(
            "DELETE FROM workspaceusergroupmembership "
            "WHERE workspace_id = :ws AND member_id = :gid"
        ), {"ws": ws, "gid": group_id})
        db.commit()

    def set_group_access(self, db: Session, ws: str, group_id: str, read_only: bool) -> dict:
        group = db.execute(text(
            "SELECT id FROM usergroup WHERE id = :gid AND workspace_id = :ws"
        ), {"gid": group_id, "ws": ws}).fetchone()
        if not group:
            raise UserGroupNotFoundException("UserGroupNotFoundException", group_id)
        db.execute(text(
            "INSERT INTO workspaceusergroupmembership "
            "(workspace_id, member_id, member_workspace_id, readonly) "
            "VALUES (:ws, :gid, :ws, :ro) "
            "ON CONFLICT (workspace_id, member_id, member_workspace_id) "
            "DO UPDATE SET readonly = :ro2"
        ), {"ws": ws, "gid": group_id, "ro": read_only, "ro2": read_only})
        db.commit()
        return {"workspaceId": ws, "memberId": group_id, "readOnly": read_only}

    def get_group_tag_subscriptions(self, db: Session, ws: str, group_id: str) -> list:
        group = db.execute(text(
            "SELECT id FROM usergroup WHERE id = :gid AND workspace_id = :ws"
        ), {"gid": group_id, "ws": ws}).fetchone()
        if not group:
            raise UserGroupNotFoundException("UserGroupNotFoundException", group_id)
        rows = db.execute(text(
            "SELECT tag_workspace_id, tag_label, oniterationchange, onstatechange "
            "FROM tagusergroupsubscription "
            "WHERE subscriber_id = :gid AND subscriber_workspace_id = :ws"
        ), {"gid": group_id, "ws": ws}).fetchall()
        return [{
            "tag": r[1],
            "onIterationChange": bool(r[2]) if r[2] is not None else False,
            "onStateChange": bool(r[3]) if r[3] is not None else False,
        } for r in rows]

    def set_group_tag_subscription(self, db: Session, ws: str, group_id: str,
                                    tag_name: str, on_iter: bool, on_state: bool) -> dict:
        group = db.execute(text(
            "SELECT id FROM usergroup WHERE id = :gid AND workspace_id = :ws"
        ), {"gid": group_id, "ws": ws}).fetchone()
        if not group:
            raise UserGroupNotFoundException("UserGroupNotFoundException", group_id)
        db.execute(text(
            "INSERT INTO tag (workspace_id, label) VALUES (:ws, :tag) ON CONFLICT DO NOTHING"
        ), {"ws": ws, "tag": tag_name})
        db.execute(text(
            "INSERT INTO tagusergroupsubscription "
            "(tag_workspace_id, tag_label, subscriber_id, subscriber_workspace_id, "
            " oniterationchange, onstatechange) "
            "VALUES (:ws, :tag, :gid, :ws, :oi, :os) "
            "ON CONFLICT (tag_workspace_id, tag_label, subscriber_id, subscriber_workspace_id) "
            "DO UPDATE SET oniterationchange = :oi2, onstatechange = :os2"
        ), {"ws": ws, "tag": tag_name, "gid": group_id,
            "oi": on_iter, "oi2": on_iter, "os": on_state, "os2": on_state})
        db.commit()
        return {"tag": tag_name, "onIterationChange": on_iter, "onStateChange": on_state}

    def delete_group_tag_subscription(self, db: Session, ws: str, group_id: str,
                                       tag_name: str):
        db.execute(text(
            "DELETE FROM tagusergroupsubscription "
            "WHERE tag_workspace_id = :ws AND tag_label = :tag "
            "AND subscriber_id = :gid AND subscriber_workspace_id = :ws"
        ), {"ws": ws, "tag": tag_name, "gid": group_id})
        db.commit()

    def get_workspace_user_groups(self, db: Session, ws: str) -> list:
        rows = db.execute(text(
            "SELECT g.id, g.workspace_id FROM usergroup g WHERE g.workspace_id = :ws"
        ), {"ws": ws}).fetchall()
        return [{"id": r[0], "workspaceId": r[1]} for r in rows]

    # ============================================================
    # Membership helpers (routers/workspace_memberships.py)
    # ============================================================

    def get_my_membership(self, db: Session, ws: str, login: str) -> dict:
        row = db.execute(text(
            "SELECT wm.readonly "
            "FROM workspaceusermembership wm "
            "WHERE wm.workspace_id = :ws AND wm.member_login = :l AND wm.member_workspace_id = :ws"
        ), {"ws": ws, "l": login}).fetchone()
        acc = db.query(Account).filter(Account.login == login).first()
        read_only = bool(row[0]) if row else True
        return {
            "workspaceId": ws,
            "member": {
                "login": login,
                "name": acc.name or "" if acc else "",
                "email": acc.email or "" if acc else "",
                "language": acc.language or "" if acc else "",
                "workspaceId": ws,
            },
            "readOnly": read_only,
        }

    def list_group_memberships(self, db: Session, ws: str) -> list:
        rows = db.execute(text(
            "SELECT wgm.workspace_id, wgm.member_id, wgm.readonly "
            "FROM workspaceusergroupmembership wgm "
            "WHERE wgm.workspace_id = :ws"
        ), {"ws": ws}).fetchall()
        if not rows:
            return []
        return [{"workspaceId": r[0], "memberId": r[1],
                 "readOnly": bool(r[2]) if r[2] is not None else False,
                 "member": {"id": r[1]}} for r in rows]

    def get_my_group_memberships(self, db: Session, ws: str, login: str) -> list:
        rows = db.execute(text(
            "SELECT g.id, g.workspace_id, COALESCE(wgm.readonly, false) "
            "FROM usergroup g "
            "JOIN usergroupmapping m ON g.id = m.groupname "
            "LEFT JOIN workspaceusergroupmembership wgm "
            "  ON wgm.member_id = g.id "
            "  AND wgm.member_workspace_id = g.workspace_id "
            "  AND wgm.workspace_id = g.workspace_id "
            "WHERE g.workspace_id = :ws AND m.login = :l"
        ), {"ws": ws, "l": login}).fetchall()
        return [{"workspaceId": r[1], "memberId": r[0], "readOnly": bool(r[2])} for r in rows]

    def remove_from_group(self, db: Session, ws: str, gid: str, login: str) -> dict:
        group = db.execute(text(
            "SELECT id, workspace_id FROM usergroup WHERE id = :gid AND workspace_id = :ws"
        ), {"gid": gid, "ws": ws}).fetchone()
        if not group:
            raise EntityNotFoundException("UserGroupNotFoundException", gid)
        db.execute(text(
            "DELETE FROM usergroupmapping WHERE login = :l AND groupname = :g"
        ), {"l": login, "g": gid})
        db.commit()
        return {"id": group.id, "workspaceId": group.workspace_id}

    def set_workspace_admin(self, db: Session, ws: str, login: str) -> dict:
        db.execute(text(
            "UPDATE workspace SET admin_login = :login WHERE id = :id"
        ), {"login": login, "id": ws})
        db.commit()

    def set_user_access(self, db: Session, ws: str, login: str, read_only: bool) -> dict:
        row = db.execute(text(
            "SELECT 1 FROM workspaceusermembership "
            "WHERE workspace_id = :ws AND member_login = :l AND member_workspace_id = :ws"
        ), {"ws": ws, "l": login}).fetchone()
        if not row:
            raise NotAllowedException("NotAllowedException9", login)
        db.execute(text(
            "UPDATE workspaceusermembership SET readonly = :ro "
            "WHERE workspace_id = :ws AND member_login = :l AND member_workspace_id = :ws"
        ), {"ws": ws, "l": login, "ro": read_only})
        db.commit()
        acc = db.query(Account).filter(Account.login == login).first()
        return {
            "login": login,
            "name": acc.name or "" if acc else "",
            "email": acc.email or "" if acc else "",
            "language": acc.language or "" if acc else "",
            "workspaceId": ws,
        }

    # ============================================================
    # User stats & admin helpers (routers/users.py + accounts.py)
    # ============================================================

    def get_users_stats(self, db: Session, ws: str) -> dict:
        users = db.execute(text(
            "SELECT COUNT(*) FROM userdata WHERE workspace_id=:w"
        ), {"w": ws}).scalar() or 0
        active_users = db.execute(text(
            "SELECT COUNT(*) FROM workspaceusermembership "
            "WHERE workspace_id = :w"
        ), {"w": ws}).scalar() or 0
        groups = db.execute(text(
            "SELECT COUNT(*) FROM usergroup WHERE workspace_id=:w"
        ), {"w": ws}).scalar() or 0
        active_groups = db.execute(text(
            "SELECT COUNT(*) FROM workspaceusergroupmembership WHERE workspace_id=:w"
        ), {"w": ws}).scalar() or 0
        return {
            "users": users,
            "activeusers": active_users,
            "inactiveusers": users - active_users,
            "groups": groups,
            "activegroups": active_groups,
            "inactivegroups": groups - active_groups,
        }

    def get_admin_user(self, db: Session, ws: str) -> dict:
        r = db.execute(text(
            "SELECT a.login, a.name, a.email, a.language "
            "FROM account a JOIN workspace w ON a.login = w.admin_login "
            "WHERE w.id = :ws"
        ), {"ws": ws}).fetchone()
        if not r:
            from app.core.exceptions import WorkspaceNotFoundException
            raise WorkspaceNotFoundException("WorkspaceNotFoundException", ws)
        return {"login": r[0], "name": r[1] or "", "email": r[2] or "",
                "language": r[3] or "", "workspaceId": ws}

    def is_account_admin(self, db: Session, login: str) -> bool:
        return db.execute(text(
            "SELECT 1 FROM usergroupmapping WHERE login = :l AND groupname = 'admin'"
        ), {"l": login}).first() is not None

    def get_accounts_stats(self, db: Session) -> dict:
        total = db.execute(text("SELECT COUNT(*) FROM account")).scalar()
        enabled = db.execute(text("SELECT COUNT(*) FROM account WHERE enabled = true")).scalar()
        disabled = total - enabled if total else 0
        return {"totalAccounts": total or 0, "enabledAccounts": enabled or 0,
                "disabledAccounts": disabled}

    def get_admin_workspace_stats(self, db: Session) -> dict:
        total = db.execute(text("SELECT COUNT(*) FROM workspace")).scalar()
        enabled = db.execute(text("SELECT COUNT(*) FROM workspace WHERE enabled = true")).scalar()
        return {"totalWorkspaces": total or 0, "enabledWorkspaces": enabled or 0}

    # ============================================================
    # Tag subscription helpers (routers/users.py)
    # ============================================================

    def get_user_tag_subscriptions(self, db: Session, ws: str, login: str) -> list:
        rows = db.execute(text(
            "SELECT tag_workspace_id, tag_label, oniterationchange, onstatechange "
            "FROM tagusersubscription "
            "WHERE subscriber_login = :l AND subscriber_workspace_id = :ws"
        ), {"l": login, "ws": ws}).fetchall()
        return [{
            "tag": r[1],
            "onIterationChange": bool(r[2]) if r[2] is not None else False,
            "onStateChange": bool(r[3]) if r[3] is not None else False,
        } for r in rows]

    def set_user_tag_subscription(self, db: Session, ws: str, login: str,
                                   tag_name: str, on_iter: bool, on_state: bool) -> dict:
        db.execute(text(
            "INSERT INTO tag (workspace_id, label) VALUES (:ws, :tag) ON CONFLICT DO NOTHING"
        ), {"ws": ws, "tag": tag_name})
        db.execute(text(
            "INSERT INTO tagusersubscription "
            "(tag_workspace_id, tag_label, subscriber_login, subscriber_workspace_id, "
            " oniterationchange, onstatechange) "
            "VALUES (:ws, :tag, :l, :ws, :oi, :os) "
            "ON CONFLICT (tag_workspace_id, tag_label, subscriber_login, subscriber_workspace_id) "
            "DO UPDATE SET oniterationchange = :oi2, onstatechange = :os2"
        ), {"ws": ws, "tag": tag_name, "l": login,
            "oi": on_iter, "oi2": on_iter, "os": on_state, "os2": on_state})
        db.commit()
        return {"tag": tag_name, "onIterationChange": on_iter, "onStateChange": on_state}

    def delete_user_tag_subscription(self, db: Session, ws: str, login: str,
                                      tag_name: str):
        db.execute(text(
            "DELETE FROM tagusersubscription "
            "WHERE tag_workspace_id = :ws AND tag_label = :tag "
            "AND subscriber_login = :l AND subscriber_workspace_id = :ws"
        ), {"ws": ws, "tag": tag_name, "l": login})
        db.commit()

    # ============================================================
    # GCM helpers (routers/accounts.py)
    # ============================================================

    def put_gcm(self, db: Session, login: str, gcm_id: str):
        db.execute(text(
            "DELETE FROM gcmaccount WHERE account_login = :login"
        ), {"login": login})
        db.execute(text(
            "INSERT INTO gcmaccount (gcmid, account_login) VALUES (:gcmid, :login)"
        ), {"gcmid": gcm_id, "login": login})
        db.commit()

    def delete_gcm(self, db: Session, login: str):
        db.execute(text(
            "DELETE FROM gcmaccount WHERE account_login = :login"
        ), {"login": login})
        db.commit()

    def is_workspace_member(self, db: Session, ws: str, login: str) -> bool:
        """检查用户是否是工作区成员（userdata 表）。"""
        return db.execute(text(
            "SELECT 1 FROM userdata WHERE login = :l AND workspace_id = :ws"
        ), {"l": login, "ws": ws}).first() is not None


user_mgmt_service = UserMgmtService()
