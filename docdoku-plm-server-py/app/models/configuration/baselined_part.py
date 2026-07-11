"""BaselinedPart ORM 模型。"""
from sqlalchemy import Column, String, Integer, ForeignKey
from app.core.database import Base

class BaselinedPart(Base):
    __tablename__ = "baselinedpart"
    productbaseline_id = Column(Integer, ForeignKey("productbaseline.id"), primary_key=True)
    partcollection_id = Column(Integer, ForeignKey("partcollection.id"), primary_key=True)
    target_workspace_id = Column("target_workspace_id", String, primary_key=True)
    target_partmaster_partnumber = Column("target_partmaster_partnumber", String, primary_key=True)
    target_partrevision_version = Column("target_partrevision_version", String)
    target_iteration = Column("target_iteration", Integer, primary_key=True)
