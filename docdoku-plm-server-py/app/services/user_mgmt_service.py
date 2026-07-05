from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.auth import Account, UserGroupMapping
from app.models.user_mgmt import UserGroup, Credential
from app.core.exceptions import (
    EntityAlreadyExistsException, EntityNotFoundException,
    EntityConstraintException, CreationException,
)
import hashlib


class UserMgmtService:
    def list_users(self, db: Session, ws: str) -> list:
        rows = db.execute(text(
            "SELECT u.login, u.workspace_id, a.name, a.email, a.enabled "
            "FROM userdata u JOIN account a ON u.login = a.login "
            "WHERE u.workspace_id = :ws"
        ), {"ws": ws}).fetchall()
        return [{"login": r[0], "workspaceId": r[1], "name": r[2],
                 "email": r[3], "enabled": r[4]} for r in rows]

    def who_am_i(self, db: Session, ws: str, login: str) -> dict:
        acc = db.query(Account).filter(Account.login == login).first()
        if not acc:
            raise EntityNotFoundException("UserNotFoundException", login)
        return {"login": acc.login, "name": acc.name, "email": acc.email,
                "language": acc.language, "timezone": acc.timezone}

    def list_groups(self, db: Session, ws: str) -> list[UserGroup]:
        return db.query(UserGroup).filter(UserGroup.workspace_id == ws).all()

    def create_group(self, db: Session, ws: str, group_id: str) -> UserGroup:
        existing = db.query(UserGroup).filter(
            UserGroup.id == group_id, UserGroup.workspace_id == ws).first()
        if existing:
            raise EntityAlreadyExistsException("UserGroupAlreadyExistsException", group_id)
        g = UserGroup(id=group_id, workspace_id=ws)
        db.add(g)
        db.commit()
        db.refresh(g)
        return g

    def delete_group(self, db: Session, ws: str, group_id: str):
        g = db.query(UserGroup).filter(
            UserGroup.id == group_id, UserGroup.workspace_id == ws).first()
        if not g:
            raise EntityNotFoundException("UserGroupNotFoundException", group_id)
        # 检查成员
        members = db.execute(text(
            "SELECT COUNT(*) FROM usergroupmapping WHERE groupname = :g"
        ), {"g": group_id}).scalar()
        if members > 0:
            raise EntityConstraintException("EntityConstraintException11")
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
        if existing == 0:
            db.execute(text(
                "INSERT INTO userdata (login, workspace_id) VALUES (:l, :w)"
            ), {"l": login, "w": ws})
        if group_id:
            db.execute(text(
                "INSERT INTO usergroupmapping (login, groupname) VALUES (:l, :g) "
                "ON CONFLICT DO NOTHING"
            ), {"l": login, "g": group_id})
        db.commit()

    def remove_user_from_workspace(self, db: Session, ws: str, login: str):
        db.execute(text(
            "DELETE FROM userdata WHERE login = :l AND workspace_id = :w"
        ), {"l": login, "w": ws})
        db.execute(text(
            "DELETE FROM usergroupmapping WHERE login = :l"
        ), {"l": login})
        db.commit()

    def enable_user(self, db: Session, ws: str, login: str):
        db.execute(text(
            "UPDATE account SET enabled = true WHERE login = :l"
        ), {"l": login})
        db.commit()

    def disable_user(self, db: Session, ws: str, login: str):
        db.execute(text(
            "UPDATE account SET enabled = false WHERE login = :l"
        ), {"l": login})
        db.commit()

    def list_memberships(self, db: Session, ws: str) -> list:
        rows = db.execute(text(
            "SELECT u.login, u.workspace_id, a.name, a.enabled "
            "FROM userdata u JOIN account a ON u.login = a.login "
            "WHERE u.workspace_id = :ws"
        ), {"ws": ws}).fetchall()
        return [{"workspaceId": ws, "member": {"login": r[0], "name": r[2]},
                 "readOnly": not r[3]} for r in rows]

    def create_account(self, db: Session, login: str, password: str,
                       email: str, name: str, lang: str) -> Account:
        existing = db.query(Account).filter(Account.login == login).first()
        if existing:
            raise EntityAlreadyExistsException("AccountAlreadyExistsException", login)
        acc = Account(login=login, email=email, name=name, language=lang)
        db.add(acc)
        cred = Credential(login=login, password=hashlib.md5(password.encode()).hexdigest())
        db.add(cred)
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
        if "timezone" in fields:
            acc.timezone = fields["timezone"]
        if "password" in fields:
            cred = db.query(Credential).filter(Credential.login == login).first()
            if cred:
                cred.password = hashlib.md5(fields["password"].encode()).hexdigest()
        db.commit()
        db.refresh(acc)
        return acc

    def list_workspaces_for_user(self, db: Session, login: str) -> list:
        rows = db.execute(text(
            "SELECT w.id, w.enabled FROM workspace w "
            "JOIN userdata u ON w.id = u.workspace_id "
            "WHERE u.login = :l"
        ), {"l": login}).fetchall()
        return [{"id": r[0], "enabled": r[1]} for r in rows]


user_mgmt_service = UserMgmtService()
