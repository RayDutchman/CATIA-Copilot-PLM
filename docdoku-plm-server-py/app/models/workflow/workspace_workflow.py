"""WorkspaceWorkflow ORM 模型。"""
from sqlalchemy import Column, String
from app.core.database import Base

class WorkspaceWorkflow(Base):
    __tablename__ = "workspaceworkflow"
    workspace_id = Column(String, primary_key=True)
    workflowmodel_id = Column(String, primary_key=True)
