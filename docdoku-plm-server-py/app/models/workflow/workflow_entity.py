"""Workflow ORM 模型，映射 workflow 表。"""
from sqlalchemy import Column, Integer, DateTime, String
from app.core.database import Base


class Workflow(Base):
    __tablename__ = "workflow"

    id = Column(Integer, primary_key=True)
    aborteddate = Column(DateTime)
    finallifecyclestate = Column(String)
