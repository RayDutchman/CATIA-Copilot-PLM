"""Role ORM 模型 + 关联表。"""
from sqlalchemy import Column, String, ForeignKey, ForeignKeyConstraint, Table
from app.core.database import Base

role_user = Table(
    "role_user", Base.metadata,
    Column("role_name", String, primary_key=True),
    Column("role_workspace_id", String, primary_key=True),
    Column("user_login", String, primary_key=True),
    Column("user_workspace_id", String, primary_key=True),
    ForeignKeyConstraint(["role_name", "role_workspace_id"],
                         ["role.name", "role.workspace_id"]),
    ForeignKeyConstraint(["user_login", "user_workspace_id"],
                         ["userdata.login", "userdata.workspace_id"]),
)

role_usergroup = Table(
    "role_usergroup", Base.metadata,
    Column("role_name", String, primary_key=True),
    Column("role_workspace_id", String, primary_key=True),
    Column("usergroup_id", String, primary_key=True),
    Column("usergroup_workspace_id", String, primary_key=True),
    ForeignKeyConstraint(["role_name", "role_workspace_id"],
                         ["role.name", "role.workspace_id"]),
    ForeignKeyConstraint(["usergroup_id", "usergroup_workspace_id"],
                         ["usergroup.id", "usergroup.workspace_id"]),
)


class Role(Base):
    __tablename__ = "role"

    name = Column(String, primary_key=True)
    workspace_id = Column(String, ForeignKey("workspace.id"), primary_key=True)
