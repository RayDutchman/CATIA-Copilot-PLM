"""Workspace ORM 模型，映射 workspace 表。"""
from sqlalchemy import Column, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Workspace(Base):
    __tablename__ = "workspace"

    id = Column(String(100), primary_key=True)
    admin_login = Column(String, ForeignKey("account.login"), nullable=False)
    description = Column(Text, nullable=True)
    folder_locked = Column(Boolean, default=False)
    enabled = Column(Boolean, default=False)

    admin = relationship("Account", foreign_keys=[admin_login])
