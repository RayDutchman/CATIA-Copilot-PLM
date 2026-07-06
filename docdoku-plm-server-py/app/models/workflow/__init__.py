"""Workflow ORM 模型。"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from app.core.database import Base

# Webhook 实体（保留在此，P0B 阶段拆分）
class WebhookApp(Base):
    __tablename__ = "webhookapp"
    id = Column(Integer, primary_key=True, autoincrement=True)
    dtype = Column(String)
    auth = Column(String)
    method = Column(String)
    uri = Column(String)
    awsaccount = Column(String)
    awssecret = Column(String)
    region = Column(String)
    topicarn = Column(String)


class Webhook(Base):
    __tablename__ = "webhook"
    id = Column(Integer, primary_key=True, autoincrement=True)
    active = Column(Boolean)
    name = Column(String)
    workspace_id = Column(String)
    webhookapp_id = Column(Integer, ForeignKey("webhookapp.id"))


# 向后兼容重新导出
from app.models.workflow.workflow_entity import Workflow  # noqa: E402, F401
from app.models.workflow.workflow_model import WorkflowModel  # noqa: E402, F401
from app.models.workflow.activity import Activity  # noqa: E402, F401
from app.models.workflow.activity_model import ActivityModel  # noqa: E402, F401
from app.models.workflow.task import Task  # noqa: E402, F401
from app.models.workflow.task_model import TaskModel  # noqa: E402, F401
from app.models.workflow.role import Role  # noqa: E402, F401
from app.models.workflow.parallel_activity import ParallelActivity  # noqa: E402, F401
from app.models.workflow.parallel_activity_model import ParallelActivityModel  # noqa: E402, F401
from app.models.workflow.sequential_activity import SequentialActivity  # noqa: E402, F401
from app.models.workflow.sequential_activity_model import SequentialActivityModel  # noqa: E402, F401
