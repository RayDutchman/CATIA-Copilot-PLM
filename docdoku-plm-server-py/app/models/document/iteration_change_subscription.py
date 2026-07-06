"""IterationChangeSubscription ORM 模型 — 订阅文档迭代变更通知。"""
from sqlalchemy import Column, String, ForeignKey
from app.models.document.subscription import Subscription

class IterationChangeSubscription(Subscription):
    __tablename__ = "iterationchangesubscription"
    __mapper_args__ = {"polymorphic_identity": "iteration_change"}
    documentmaster_id = Column(String, primary_key=True)
    documentrevision_version = Column(String, primary_key=True)
    documentmaster_workspace_id = Column(String, primary_key=True)
