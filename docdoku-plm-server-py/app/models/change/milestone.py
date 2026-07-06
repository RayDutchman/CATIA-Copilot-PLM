"""Milestone ORM 模型，映射 milestone 表。"""
from sqlalchemy import Column, String, Integer, DateTime, Text
from app.core.database import Base


class Milestone(Base):
    __tablename__ = "milestone"

    id = Column(Integer, primary_key=True)
    title = Column(String)
    description = Column(Text)
    due_date = Column("duedate", DateTime)
    workspace_id = Column(String)
    acl_id = Column(Integer)
