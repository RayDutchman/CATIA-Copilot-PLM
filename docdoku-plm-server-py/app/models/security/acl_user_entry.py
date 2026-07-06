"""AclUserEntry ORM 模型，映射 acluserentry 表。"""
from sqlalchemy import Column, String, Integer, ForeignKey
from app.core.database import Base


class AclUserEntry(Base):
    __tablename__ = "acluserentry"

    acl_id = Column(Integer, ForeignKey("acl.id"), primary_key=True)
    principal_login = Column(String, primary_key=True)
    principal_workspace_id = Column(String, primary_key=True)
    permission = Column(Integer)
