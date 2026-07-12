"""组织管理——对标 Payara OrganizationManagerBean。

管理组织（Organization）的 CRUD 和成员管理。
"""
from sqlalchemy.orm import Session
from sqlalchemy import text


class OrganizationService:
    """组织管理服务。"""

    def get_org_by_name(self, db: Session, name: str) -> dict | None:
        row = db.execute(text(
            "SELECT name, description, owner_login FROM organization WHERE name = :n"
        ), {"n": name}).first()
        return dict(row._mapping) if row else None

    def list_user_organizations(self, db: Session, login: str) -> dict | None:
        row = db.execute(text(
            "SELECT o.name, o.description, o.owner_login FROM organization o "
            "JOIN organization_account oa ON o.name = oa.organization_name "
            "WHERE oa.account_login = :l"
        ), {"l": login}).first()
        return dict(row._mapping) if row else None

    def create_organization(self, db: Session, name: str,
                            description: str, owner: str) -> dict:
        existing = db.execute(text(
            "SELECT 1 FROM organization WHERE name = :n"
        ), {"n": name}).first()
        if existing:
            from app.core.exceptions import EntityAlreadyExistsException
            raise EntityAlreadyExistsException("OrganizationAlreadyExistsException", name)
        db.execute(text(
            "INSERT INTO organization (name, description, owner_login) VALUES (:n, :d, :o)"
        ), {"n": name, "d": description, "o": owner})
        db.commit()
        return {"name": name, "description": description, "owner": owner}

    def update_organization_desc(self, db: Session, name: str,
                                  description: str) -> None:
        db.execute(text(
            "UPDATE organization SET description = :d WHERE name = :n"
        ), {"d": description, "n": name})
        db.commit()

    def delete_org(self, db: Session, name: str) -> None:
        db.execute(text(
            "DELETE FROM organization_account WHERE organization_name = :n"
        ), {"n": name})
        db.execute(text(
            "DELETE FROM organization WHERE name = :n"
        ), {"n": name})
        db.commit()

    def add_member(self, db: Session, org_name: str, login: str) -> bool:
        existing = db.execute(text(
            "SELECT 1 FROM organization_account "
            "WHERE organization_name = :org AND account_login = :login"
        ), {"org": org_name, "login": login}).first()
        if existing:
            return False
        max_order = db.execute(text(
            "SELECT COALESCE(MAX(account_order), 0) FROM organization_account "
            "WHERE organization_name = :org"
        ), {"org": org_name}).scalar()
        db.execute(text(
            "INSERT INTO organization_account "
            "(organization_name, account_login, account_order) "
            "VALUES (:org, :login, :ord)"
        ), {"org": org_name, "login": login, "ord": max_order + 1})
        db.commit()
        return True

    def remove_member(self, db: Session, org_name: str, login: str) -> None:
        db.execute(text(
            "DELETE FROM organization_account "
            "WHERE organization_name = :org AND account_login = :login"
        ), {"org": org_name, "login": login})
        db.commit()

    def get_members_ordered(self, db: Session, org_name: str) -> list:
        rows = db.execute(text(
            "SELECT account_login, account_order FROM organization_account "
            "WHERE organization_name = :org ORDER BY account_order"
        ), {"org": org_name}).fetchall()
        return [(r[0], r[1]) for r in rows]

    def swap_member_order(self, db: Session, org_name: str,
                           login1: str, order1: int,
                           login2: str, order2: int) -> None:
        db.execute(text(
            "UPDATE organization_account SET account_order = :ord "
            "WHERE organization_name = :org AND account_login = :login"
        ), {"ord": order2, "org": org_name, "login": login1})
        db.execute(text(
            "UPDATE organization_account SET account_order = :ord "
            "WHERE organization_name = :org AND account_login = :login"
        ), {"ord": order1, "org": org_name, "login": login2})
        db.commit()


organization_service = OrganizationService()
