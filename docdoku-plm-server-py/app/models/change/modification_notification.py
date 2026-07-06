"""ModificationNotification ORM 模型，映射 modificationnotification 表。"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime
from app.core.database import Base


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
