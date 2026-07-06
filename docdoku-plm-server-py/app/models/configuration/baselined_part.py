"""BaselinedPart ORM 模型。"""
from sqlalchemy import Column, String, Integer, ForeignKey
from app.core.database import Base

class BaselinedPart(Base):
    __tablename__ = "baselinedpart"
    productbaseline_id = Column(Integer, ForeignKey("productbaseline.id"), primary_key=True)
    partcollection_id = Column(Integer, ForeignKey("partcollection.id"), primary_key=True)
