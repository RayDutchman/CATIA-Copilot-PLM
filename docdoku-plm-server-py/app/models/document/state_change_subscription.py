"""StateChangeSubscription ORM 模型 — 订阅文档状态变更通知。"""
from sqlalchemy import Column, String
from app.models.document.subscription import Subscription

class StateChangeSubscription(Subscription):
    __tablename__ = "statechangesubscription"
    __mapper_args__ = {"polymorphic_identity": "state_change"}
    documentmaster_id = Column(String, primary_key=True)
    documentrevision_version = Column(String, primary_key=True)
    documentmaster_workspace_id = Column(String, primary_key=True)
