"""Task ORM 模型，映射 task 表。"""
from sqlalchemy import Column, String, Integer, DateTime, Text
from app.core.database import Base


class Task(Base):
    __tablename__ = "task"

    num = Column(Integer, primary_key=True)
    activity_step = Column(Integer, primary_key=True)
    workflow_id = Column(Integer, primary_key=True)
    title = Column(String)
    instructions = Column(Text)
    status = Column(Integer)
    worker_login = Column(String)
    worker_workspace_id = Column(String)
    duration = Column(Integer)
    signature = Column(Text)
    closuredate = Column(DateTime)
    closurecomment = Column(String)
    startdate = Column(DateTime)
    targetiteration = Column(Integer)
