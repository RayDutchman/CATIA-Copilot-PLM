"""SequentialActivityModel ORM 模型 — 继承 ActivityModel，串行活动模型。"""
from app.models.workflow.activity_model import ActivityModel


class SequentialActivityModel(ActivityModel):
    __mapper_args__ = {"polymorphic_identity": "sequential_model"}
