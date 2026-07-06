"""UserGroupMapping ORM 模型，映射 usergroupmapping 表。"""
from sqlalchemy import Column, String
from app.core.database import Base


class UserGroupMapping(Base):
    __tablename__ = "usergroupmapping"

    login = Column(String, primary_key=True)
    groupname = Column(String)
