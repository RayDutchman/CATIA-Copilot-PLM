"""Account 管理服务——对标 Payara AccountManagerBean。

从 user_manager.py 拆出账户创建/更新/查询逻辑。
"""
import hashlib
from sqlalchemy.orm import Session
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
                       email: str, name: str, lang: str) -> Account:
        existing = db.query(Account).filter(Account.login == login).first()
        if existing:
            raise EntityAlreadyExistsException("AccountAlreadyExistsException", login)
        acc = Account(login=login, email=email, name=name, language=lang)
        db.add(acc)
        # MD5 哈希必须保持不变：与 Payara credential 表格式一致，
        # 更换算法会导致已存密码验证失败。
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
                # MD5 哈希必须保持不变：与 Payara credential 表格式一致
                cred.password = hashlib.md5(fields["password"].encode()).hexdigest()
        db.commit()
        db.refresh(acc)
        return acc


account_service = AccountService()
