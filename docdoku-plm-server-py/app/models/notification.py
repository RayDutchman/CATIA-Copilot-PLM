"""通知/订阅相关模型。ModificationNotification 已移至 models.change。"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Table
from app.core.database import Base

iteration_change_subscription = Table(
    "iterationchangesubscription", Base.metadata,
    Column("documentmaster_id", String, primary_key=True),
    Column("documentrevision_version", String, primary_key=True),
    Column("documentmaster_workspace_id", String, primary_key=True),
    Column("subscriber_login", String, primary_key=True),
    Column("subscriber_workspace_id", String, primary_key=True),
)

state_change_subscription = Table(
    "statechangesubscription", Base.metadata,
    Column("documentmaster_id", String, primary_key=True),
    Column("documentrevision_version", String, primary_key=True),
    Column("documentmaster_workspace_id", String, primary_key=True),
    Column("subscriber_login", String, primary_key=True),
    Column("subscriber_workspace_id", String, primary_key=True),
)

# 向后兼容：从新位置重新导出
from app.models.change.modification_notification import ModificationNotification  # noqa: E402, F401
