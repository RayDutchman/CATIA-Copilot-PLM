"""SequentialActivity ORM 模型 — 继承 Activity，串行活动。"""
from app.models.workflow.activity import Activity


class SequentialActivity(Activity):
    __mapper_args__ = {"polymorphic_identity": "sequential"}
