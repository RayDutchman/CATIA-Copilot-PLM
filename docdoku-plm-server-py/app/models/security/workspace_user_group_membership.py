"""WorkspaceUserGroupMembership ORM 模型。"""
from sqlalchemy import Column, String, Boolean
from app.core.database import Base

class WorkspaceUserGroupMembership(Base):
    __tablename__ = "workspaceusergroupmembership"
    workspace_id = Column(String, primary_key=True)
    member_workspace_id = Column(String, primary_key=True)
    member_id = Column(String, primary_key=True)
    read_only = Column("readonly", Boolean, default=False)
