"""BaselinedDocument ORM 模型。"""
from sqlalchemy import Column, String, Integer, ForeignKey
from app.core.database import Base

class BaselinedDocument(Base):
    __tablename__ = "baselineddocument"
    documentbaseline_id = Column(Integer, ForeignKey("documentbaseline.id"), primary_key=True)
    documentcollection_id = Column(Integer, ForeignKey("documentcollection.id"), primary_key=True)
