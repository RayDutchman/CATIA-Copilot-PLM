"""AclUserGroupEntry ORM 模型，映射 aclusergroupentry 表。"""
from sqlalchemy import Column, String, Integer, ForeignKey
from app.core.database import Base


class AclUserGroupEntry(Base):
    __tablename__ = "aclusergroupentry"

    acl_id = Column(Integer, ForeignKey("acl.id"), primary_key=True)
    principal_id = Column(String, primary_key=True)
    principal_workspace_id = Column(String, primary_key=True)
    permission = Column(Integer)
