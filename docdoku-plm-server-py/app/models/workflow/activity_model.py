"""ActivityModel ORM 模型，映射 activitymodel 表。"""
from sqlalchemy import Column, String, Integer, ForeignKey
from app.core.database import Base


class ActivityModel(Base):
    __tablename__ = "activitymodel"

    id = Column(Integer, primary_key=True, autoincrement=True)
    step = Column(Integer)
    dtype = Column(String)
    lifecyclestate = Column(String)
    workflowmodel_id = Column(String, ForeignKey("workflowmodel.id"))
    workspace_id = Column(String)
    taskstocomplete = Column(Integer)
