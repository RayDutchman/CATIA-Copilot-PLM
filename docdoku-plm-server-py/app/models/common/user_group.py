"""UserGroup ORM 模型，映射 usergroup 表。"""
from sqlalchemy import Column, String, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.core.database import Base


usergroup_user = Table(
    "usergroup_user", Base.metadata,
    Column("usergroup_id", String, primary_key=True),
    Column("usergroup_id_workspace_id", String, primary_key=True),
    Column("user_login", String, primary_key=True),
    Column("user_workspace_id", String, primary_key=True),
)


class UserGroup(Base):
    __tablename__ = "usergroup"

    id = Column(String(100), primary_key=True)
    workspace_id = Column(String, ForeignKey("workspace.id"), primary_key=True)

    workspace = relationship("Workspace", foreign_keys=[workspace_id])
    users = relationship("User", secondary=usergroup_user)
