"""ACL ORM 模型，映射 acl 表。"""
from sqlalchemy import Column, Integer, Boolean
from app.core.database import Base


class ACL(Base):
    __tablename__ = "acl"

    id = Column(Integer, primary_key=True, autoincrement=True)
    enabled = Column(Boolean)
