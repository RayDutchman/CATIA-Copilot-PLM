"""TaskModel ORM 模型，映射 taskmodel 表。"""
from sqlalchemy import Column, String, Integer, Text
from app.core.database import Base


class TaskModel(Base):
    __tablename__ = "taskmodel"

    num = Column(Integer, primary_key=True)
    activitymodel_id = Column(Integer, primary_key=True)
    title = Column(String)
    instructions = Column(Text)
    duration = Column(Integer)
    role_workspace_id = Column(String)
    role_name = Column(String)
