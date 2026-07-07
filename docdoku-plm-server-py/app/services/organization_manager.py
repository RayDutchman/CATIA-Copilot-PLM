"""组织管理——对标 Payara OrganizationManagerBean。

管理组织（Organization）的 CRUD 和成员管理。
"""
from sqlalchemy.orm import Session
from sqlalchemy import text


class OrganizationService:
    """组织管理服务。"""

    def get_organization_of_account(self, db: Session, login: str) -> dict:
        row = db.execute(text(
            "SELECT o.* FROM organization o "
            "JOIN account a ON a.organization_name = o.name "
            "WHERE a.login = :l"
        ), {"l": login}).first()
        if not row:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("OrganizationNotFoundException", login)
        return dict(row._mapping)

    def get_my_organization(self, db: Session, login: str) -> dict:
        return self.get_organization_of_account(db, login)

    def create_organization(self, db: Session, name: str,
                             description: str, owner_login: str) -> dict:
        existing = db.execute(text(
            "SELECT 1 FROM organization WHERE name = :n"
        ), {"n": name}).first()
        if existing:
            from app.core.exceptions import EntityAlreadyExistsException
            raise EntityAlreadyExistsException("OrganizationAlreadyExistsException", name)
        db.execute(text(
            "INSERT INTO organization (name, description, owner_login) VALUES (:n, :d, :o)"
        ), {"n": name, "d": description, "o": owner_login})
        db.commit()
        return {"name": name, "description": description, "ownerLogin": owner_login}

    def delete_organization(self, db: Session, name: str) -> None:
        db.execute(text("DELETE FROM organization WHERE name = :n"), {"n": name})
        db.commit()

    def update_organization(self, db: Session, name: str, fields: dict) -> dict:
        if "description" in fields:
            db.execute(text(
                "UPDATE organization SET description = :d WHERE name = :n"
            ), {"d": fields["description"], "n": name})
        db.commit()
        return self.get_organization_of_account(db, name)

    def add_account_in_organization(self, db: Session, org_name: str,
                                     login: str) -> None:
        db.execute(text(
            "UPDATE account SET organization_name = :o WHERE login = :l"
        ), {"o": org_name, "l": login})
        db.commit()

    def remove_accounts_from_organization(self, db: Session, org_name: str,
                                           logins: list) -> None:
        for login in logins:
            db.execute(text(
                "UPDATE account SET organization_name = NULL WHERE login = :l"
            ), {"l": login})
        db.commit()


organization_service = OrganizationService()
