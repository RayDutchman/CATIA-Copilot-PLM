from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Table
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


class ModificationNotification(Base):
    __tablename__ = "modificationnotification"
    id = Column(Integer, primary_key=True, autoincrement=True)
    acknowledged = Column(Boolean)
    acknowledgementcomment = Column(String)
    acknowledgementdate = Column(DateTime)
    ackauthor_workspace_id = Column(String)
    ackauthor_login = Column(String)
    impacted_partrevision_version = Column(String)
    impacted_iteration = Column(Integer)
    impacted_workspace_id = Column(String)
    impacted_partmaster_partnumber = Column(String)
    modified_workspace_id = Column(String)
    modified_partmaster_partnumber = Column(String)
    modified_iteration = Column(Integer)
    modified_partrevision_version = Column(String)
