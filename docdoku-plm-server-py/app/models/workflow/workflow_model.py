"""WorkflowModel ORM 模型，映射 workflowmodel 表。"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from app.core.database import Base


class WorkflowModel(Base):
    __tablename__ = "workflowmodel"

    id = Column(String, primary_key=True)
    workspace_id = Column(String, primary_key=True)
    finalLifecycleState = Column("finallifecyclestate", String)
    creationdate = Column(DateTime)
    author_workspace_id = Column(String)
    author_login = Column(String)
    acl_id = Column(Integer, ForeignKey("acl.id"))
