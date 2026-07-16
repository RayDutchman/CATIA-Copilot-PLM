"""Account 管理服务——对标 Payara AccountManagerBean。

从 user_manager.py 拆出账户创建/更新/查询逻辑。
"""
import hashlib
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.auth import Account
from app.models.user_mgmt import Credential
from app.core.exceptions import (
    EntityAlreadyExistsException, EntityNotFoundException,
)


class AccountService:

    def who_am_i(self, db: Session, ws: str, login: str) -> dict:
        acc = db.query(Account).filter(Account.login == login).first()
        if not acc:
            raise EntityNotFoundException("UserNotFoundException", login)
        return {
            "login": acc.login, "name": acc.name, "email": acc.email,
            "language": acc.language,
            "workspaceId": ws,
        }

    def create_account(self, db: Session, login: str, password: str,
                       email: str, name: str, language: str,
                       timezone: str = "") -> Account:
        existing = db.query(Account).filter(Account.login == login).first()
        if existing:
            raise EntityAlreadyExistsException("AccountAlreadyExistsException", login)
        # Java AccountManagerBean.createAccount：写入 login/name/email/language/timeZone
        acc = Account(login=login, email=email, name=name, language=language,
                      timezone=timezone)
        db.add(acc)
        # MD5 哈希必须保持不变：与 Payara credential 表格式一致，
        # 更换算法会导致已存密码验证失败。
        cred = Credential(login=login, password=hashlib.md5(password.encode()).hexdigest())
        db.add(cred)
        # 对齐 Java AccountDAO.createAccount:55 —— 同步写入默认角色组 users
        db.execute(text(
            "INSERT INTO usergroupmapping (login, groupname) VALUES (:l, 'users')"
        ), {"l": login})
        db.commit()
        db.refresh(acc)
        return acc

    def update_account(self, db: Session, login: str, fields: dict) -> Account:
        acc = db.query(Account).filter(Account.login == login).first()
        if not acc:
            raise EntityNotFoundException("AccountNotFoundException", login)
        if "email" in fields:
            acc.email = fields["email"]
        if "name" in fields:
            acc.name = fields["name"]
        if "language" in fields:
            acc.language = fields["language"]
        # Java AccountDTO.timeZone（驼峰），与前端一致
        if "timeZone" in fields:
            acc.timezone = fields["timeZone"]
        # Java AccountResource.updateAccount: accountDTO.getNewPassword() 写入新密码
        # "password" 字段是旧密码（身份验证用），"newPassword" 才是要写入的新密码
        new_password = fields.get("newPassword") or fields.get("password")
        if new_password:
            cred = db.query(Credential).filter(Credential.login == login).first()
            if cred:
                # MD5 哈希必须保持不变：与 Payara credential 表格式一致
                cred.password = hashlib.md5(new_password.encode()).hexdigest()
        db.commit()
        db.refresh(acc)
        return acc


    # ============================================================
    # Admin endpoints
    # ============================================================

    def list_accounts_admin(self, db: Session) -> list:
        return db.execute(text(
            "SELECT a.login, a.email, a.name, a.language, a.enabled, u.workspace_id, "
            "CASE WHEN m.groupname IS NOT NULL THEN true ELSE false END AS is_admin "
            "FROM account a "
            "LEFT JOIN userdata u ON a.login = u.login "
            "LEFT JOIN usergroupmapping m ON a.login = m.login AND m.groupname = 'admin' "
            "ORDER BY a.login"
        )).fetchall()

    def get_account_admin(self, db: Session, login: str):
        return db.execute(text(
            "SELECT a.login, a.email, a.name, a.language, a.enabled, u.workspace_id, "
            "CASE WHEN m.groupname IS NOT NULL THEN true ELSE false END AS is_admin "
            "FROM account a "
            "LEFT JOIN userdata u ON a.login = u.login "
            "LEFT JOIN usergroupmapping m ON a.login = m.login AND m.groupname = 'admin' "
            "WHERE a.login = :login"
        ), {"login": login}).fetchone()

    def update_account_admin(self, db: Session, login: str, body: dict):
        existing = db.execute(text(
            "SELECT login FROM account WHERE login = :login"
        ), {"login": login}).fetchone()
        if not existing:
            raise EntityNotFoundException("AccountNotFoundException", login)

        updates = {}
        if "email" in body:
            updates["email"] = body["email"]
        if "language" in body:
            updates["language"] = body["language"]
        if "enabled" in body:
            updates["enabled"] = body["enabled"]
        if "name" in body:
            updates["name"] = body["name"]

        if updates:
            set_clause = ", ".join(f"{k} = :{k}" for k in updates)
            db.execute(text(
                f"UPDATE account SET {set_clause} WHERE login = :login"
            ), {**updates, "login": login})
            db.commit()

        return self.get_account_admin(db, login)

    def delete_account_cascade(self, db: Session, login: str) -> None:
        existing = db.execute(text(
            "SELECT login FROM account WHERE login = :login"
        ), {"login": login}).fetchone()
        if not existing:
            raise EntityNotFoundException("AccountNotFoundException", login)

        # P5-21: 在 replica 模式前，于正常 FK 约束下置空所有引用 login 的列，
        # 避免删除 account 后残留 dangling FK 引用。
        author_tables = [
            "changeissue", "changeorder", "changerequest",
            "configurationitem", "documentbaseline", "documentcollection",
            "documentiteration", "documentmaster", "documentmastertemplate",
            "documentrevision", "layer", "marker",
            "partcollection", "partiteration", "partmaster", "partmastertemplate",
            "partrevision", "productbaseline", "productconfiguration",
            "productinstanceiteration", "query", "sharedentity", "workflowmodel",
        ]
        for t in author_tables:
            db.execute(text(f"UPDATE {t} SET author_login = NULL WHERE author_login = :login"), {"login": login})

        for t in ["changeissue", "changeorder", "changerequest"]:
            db.execute(text(f"UPDATE {t} SET assignee_login = NULL WHERE assignee_login = :login"), {"login": login})

        for t in ["documentrevision", "partrevision"]:
            db.execute(text(f"UPDATE {t} SET checkoutuser_login = NULL WHERE checkoutuser_login = :login"), {"login": login})
            db.execute(text(f"UPDATE {t} SET obsolete_user_login = NULL WHERE obsolete_user_login = :login"), {"login": login})
            db.execute(text(f"UPDATE {t} SET release_user_login = NULL WHERE release_user_login = :login"), {"login": login})

        db.execute(text("UPDATE import SET user_login = NULL WHERE user_login = :login"), {"login": login})
        db.execute(text("UPDATE modificationnotification SET ackauthor_login = NULL WHERE ackauthor_login = :login"), {"login": login})
        db.execute(text("UPDATE organization SET owner_login = NULL WHERE owner_login = :login"), {"login": login})
        db.execute(text("UPDATE task SET worker_login = NULL WHERE worker_login = :login"), {"login": login})

        for t in ["documentlog", "partlog", "workspacelog"]:
            db.execute(text(f"UPDATE {t} SET userlogin = NULL WHERE userlogin = :login"), {"login": login})

        # NOT NULL 外键列 → 必须先删记录（引用 userdata，userdata 随后被删）
        db.execute(text("DELETE FROM acluserentry WHERE principal_login = :login"), {"login": login})
        db.execute(text("DELETE FROM task_user WHERE user_login = :login"), {"login": login})

        # 关 FK 触发器，安全清理所有引用 account.login 的关联表
        db.execute(text("SET LOCAL session_replication_role='replica'"))

        # 组织和 GCM
        db.execute(text("DELETE FROM organization_account WHERE account_login = :login"), {"login": login})
        db.execute(text("DELETE FROM gcmaccount WHERE account_login = :login"), {"login": login})
        # 密码恢复请求 / OAuth
        db.execute(text("DELETE FROM passwordrecoveryrequest WHERE login = :login"), {"login": login})
        db.execute(text("DELETE FROM providedaccount WHERE login = :login"), {"login": login})
        # 工作区成员 + 用户组用户
        db.execute(text("DELETE FROM workspaceusermembership WHERE member_login = :login"), {"login": login})
        db.execute(text("DELETE FROM usergroup_user WHERE user_login = :login"), {"login": login})
        # 角色
        db.execute(text("DELETE FROM role_user WHERE user_login = :login"), {"login": login})
        # 标签订阅
        db.execute(text("DELETE FROM tagusersubscription WHERE subscriber_login = :login"), {"login": login})
        # 迭代/状态变更订阅
        db.execute(text("DELETE FROM iterationchangesubscription WHERE subscriber_login = :login"), {"login": login})
        db.execute(text("DELETE FROM statechangesubscription WHERE subscriber_login = :login"), {"login": login})
        # 工作区管理权——由该用户管理的 workspace 置空 admin_login
        db.execute(text("UPDATE workspace SET admin_login = NULL WHERE admin_login = :login"), {"login": login})
        # 凭据
        db.execute(text("DELETE FROM credential WHERE login = :login"), {"login": login})
        # userdata
        db.execute(text("DELETE FROM userdata WHERE login = :login"), {"login": login})
        # 用户组映射
        db.execute(text("DELETE FROM usergroupmapping WHERE login = :login"), {"login": login})
        # 账号本身
        db.execute(text("DELETE FROM account WHERE login = :login"), {"login": login})

        db.execute(text("SET LOCAL session_replication_role='origin'"))
        db.commit()

    def enable_account_admin(self, db: Session, login: str, enabled: bool):
        existing = db.execute(text(
            "SELECT login FROM account WHERE login = :login"
        ), {"login": login}).fetchone()
        if not existing:
            raise EntityNotFoundException("AccountNotFoundException", login)
        db.execute(text("UPDATE account SET enabled = :e WHERE login = :l"),
                   {"e": enabled, "l": login})
        db.commit()
        return self.get_account_admin(db, login)

    # ============================================================
    # Admin stats
    # ============================================================

    def _get_admin_workspaces(self, db: Session, login: str) -> list[str]:
        """返回当前用户管理的 workspace 列表（全局 admin 看全部）。"""
        is_global = db.execute(text(
            "SELECT COUNT(*) FROM usergroupmapping WHERE login=:l AND groupname='admin'"
        ), {"l": login}).scalar() > 0
        if is_global:
            rows = db.execute(text("SELECT id FROM workspace ORDER BY id")).fetchall()
            return [r[0] for r in rows]
        rows = db.execute(text(
            "SELECT id FROM workspace WHERE admin_login=:l ORDER BY id"
        ), {"l": login}).fetchall()
        return [r[0] for r in rows]

    def get_disk_usage_stats(self, db: Session, login: str) -> dict:
        ws_list = self._get_admin_workspaces(db, login)
        result = {}
        for ws in ws_list:
            docs_size = db.execute(text(
                "SELECT COALESCE(SUM(br.contentlength), 0) FROM binaryresource br "
                "JOIN documentiteration_binres dib ON br.fullname = dib.attachedfile_fullname "
                "WHERE dib.workspace_id = :ws"
            ), {"ws": ws}).scalar() or 0
            parts_size = db.execute(text(
                "SELECT COALESCE(SUM(br.contentlength), 0) FROM binaryresource br "
                "JOIN partiteration_binres pib ON br.fullname = pib.attachedfile_fullname "
                "WHERE pib.workspace_id = :ws"
            ), {"ws": ws}).scalar() or 0
            result[ws] = docs_size + parts_size
        return result

    def get_users_stats(self, db: Session, login: str) -> dict:
        ws_list = self._get_admin_workspaces(db, login)
        result = {}
        for ws in ws_list:
            result[ws] = db.execute(text(
                "SELECT COUNT(*) FROM userdata WHERE workspace_id=:ws"
            ), {"ws": ws}).scalar() or 0
        return result

    def get_documents_stats(self, db: Session, login: str) -> dict:
        ws_list = self._get_admin_workspaces(db, login)
        result = {}
        for ws in ws_list:
            result[ws] = db.execute(text(
                "SELECT COUNT(*) FROM documentrevision WHERE workspace_id=:ws"
            ), {"ws": ws}).scalar() or 0
        return result

    def get_products_stats(self, db: Session, login: str) -> dict:
        ws_list = self._get_admin_workspaces(db, login)
        result = {}
        for ws in ws_list:
            result[ws] = db.execute(text(
                "SELECT COUNT(*) FROM configurationitem WHERE workspace_id=:ws"
            ), {"ws": ws}).scalar() or 0
        return result

    def get_parts_stats(self, db: Session, login: str) -> dict:
        ws_list = self._get_admin_workspaces(db, login)
        result = {}
        for ws in ws_list:
            result[ws] = db.execute(text(
                "SELECT COUNT(*) FROM partrevision WHERE workspace_id=:ws"
            ), {"ws": ws}).scalar() or 0
        return result


account_service = AccountService()
