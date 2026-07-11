"""BaselinedDocument ORM 模型，映射 baselineddocument 表。"""
from sqlalchemy import Column, String, Integer, ForeignKey
from app.core.database import Base


class BaselinedDocument(Base):
    __tablename__ = "baselineddocument"

    documentcollection_id = Column(Integer, ForeignKey("documentcollection.id"), primary_key=True)
    target_workspace_id = Column(String, primary_key=True)
    target_documentmaster_id = Column(String, primary_key=True)
    target_docrevision_version = Column(String, primary_key=True)
    target_iteration = Column(Integer)
