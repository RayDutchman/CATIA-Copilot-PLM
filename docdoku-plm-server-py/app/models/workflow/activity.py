"""Activity ORM 模型，映射 activity 表。"""
from sqlalchemy import Column, String, Integer, ForeignKey
from app.core.database import Base


class Activity(Base):
    __tablename__ = "activity"

    step = Column(Integer, primary_key=True)
    workflow_id = Column(Integer, ForeignKey("workflow.id"), primary_key=True)
    dtype = Column(String)
    lifecyclestate = Column(String)
    taskstocomplete = Column(Integer)
