"""ParallelActivity ORM 模型 — 继承 Activity，并行活动。"""
from app.models.workflow.activity import Activity


class ParallelActivity(Activity):
    """对应 Java ParallelActivity extends Activity。SINGLE_TABLE 继承。"""
    __mapper_args__ = {"polymorphic_identity": "parallel"}
