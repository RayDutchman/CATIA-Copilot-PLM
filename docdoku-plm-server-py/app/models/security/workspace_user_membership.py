"""WorkspaceUserMembership ORM 模型。"""
from sqlalchemy import Column, String, Boolean
from app.core.database import Base

class WorkspaceUserMembership(Base):
    __tablename__ = "workspaceusermembership"
    workspace_id = Column(String, primary_key=True)
    member_workspace_id = Column(String, primary_key=True)
    member_login = Column(String, primary_key=True)
    read_only = Column("readonly", Boolean, default=False)
