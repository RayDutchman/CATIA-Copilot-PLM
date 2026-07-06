"""ParallelActivityModel ORM 模型 — 继承 ActivityModel，并行活动模型。"""
from app.models.workflow.activity_model import ActivityModel


class ParallelActivityModel(ActivityModel):
    __mapper_args__ = {"polymorphic_identity": "parallel_model"}
