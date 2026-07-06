"""角色管理服务——CRUD 操作。"""
from sqlalchemy.orm import Session
from app.models.security import Role, role_user, role_usergroup
from app.core.exceptions import (
    EntityAlreadyExistsException, EntityConstraintException,
    EntityNotFoundException, RoleAlreadyExistsException,
    RoleNotFoundException,
)
from sqlalchemy import text


class SecurityService:
    def list_roles(self, db: Session, ws: str) -> list[Role]:
        return db.query(Role).filter(Role.workspace_id == ws).all()

    def list_roles_in_use(self, db: Session, ws: str) -> list[Role]:
        roles = self.list_roles(db, ws)
        result = []
        for r in roles:
            user_count = db.execute(text(
                "SELECT COUNT(*) FROM role_user WHERE role_name=:n AND role_workspace_id=:w"
            ), {"n": r.name, "w": ws}).scalar()
            group_count = db.execute(text(
                "SELECT COUNT(*) FROM role_usergroup WHERE role_name=:n AND role_workspace_id=:w"
            ), {"n": r.name, "w": ws}).scalar()
            if user_count > 0 or group_count > 0:
                result.append(r)
        return result

    def create_role(self, db: Session, ws: str, name: str,
                    default_users: list | None = None,
                    default_groups: list | None = None) -> Role:
        existing = db.query(Role).filter(Role.name == name, Role.workspace_id == ws).first()
        if existing:
            raise RoleAlreadyExistsException("RoleAlreadyExistsException", name)
        role = Role(name=name, workspace_id=ws)
        db.add(role)
        db.commit()
        db.refresh(role)
        self._update_role_assignments(db, ws, name, default_users, default_groups)
        return role

    def update_role(self, db: Session, ws: str, name: str,
                    default_users: list | None = None,
                    default_groups: list | None = None) -> Role:
        role = db.query(Role).filter(Role.name == name, Role.workspace_id == ws).first()
        if not role:
            raise RoleNotFoundException("RoleNotFoundException", name)
        self._update_role_assignments(db, ws, name, default_users, default_groups)
        return role

    def delete_role(self, db: Session, ws: str, name: str):
        role = db.query(Role).filter(Role.name == name, Role.workspace_id == ws).first()
        if not role:
            raise RoleNotFoundException("RoleNotFoundException", name)
        rows = db.execute(text(
            "SELECT COUNT(*) FROM role_user WHERE role_name=:n AND role_workspace_id=:w "
            "UNION ALL SELECT COUNT(*) FROM role_usergroup WHERE role_name=:n AND role_workspace_id=:w"
        ), {"n": name, "w": ws}).fetchall()
        if any(r[0] > 0 for r in rows):
            raise EntityConstraintException("EntityConstraintException25")
        db.delete(role)
        db.commit()

    def _update_role_assignments(self, db: Session, ws: str, name: str,
                                 users: list | None, groups: list | None):
        db.execute(role_user.delete().where(
            role_user.c.role_name == name,
            role_user.c.role_workspace_id == ws,
        ))
        db.execute(role_usergroup.delete().where(
            role_usergroup.c.role_name == name,
            role_usergroup.c.role_workspace_id == ws,
        ))
        if users:
            for u in users:
                db.execute(role_user.insert().values(
                    role_name=name, role_workspace_id=ws,
                    user_login=u.get("login", ""), user_workspace_id=ws,
                ))
        if groups:
            for g in groups:
                db.execute(role_usergroup.insert().values(
                    role_name=name, role_workspace_id=ws,
                    usergroup_id=g.get("id", ""), usergroup_workspace_id=ws,
                ))
        db.commit()


security_service = SecurityService()
