"""BaselinedDocumentBinaryResourceCollection ORM 模型。"""
from sqlalchemy import Column, String, Integer, ForeignKey
from app.core.database import Base

class BaselinedDocumentBinaryResourceCollection(Base):
    __tablename__ = "baselinedocumentbinrescollection"
    documentbaseline_id = Column(Integer, ForeignKey("documentbaseline.id"), primary_key=True)
    binrescollection_id = Column(Integer, primary_key=True)
