"""User (USERDATA) ORM 模型，映射 userdata 表。"""
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "userdata"

    workspace_id = Column(String, ForeignKey("workspace.id"), primary_key=True)
    login = Column(String, ForeignKey("account.login"), primary_key=True)

    account = relationship("Account", foreign_keys=[login])
    workspace = relationship("Workspace", foreign_keys=[workspace_id])
