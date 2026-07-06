"""StatusChange @Embeddable。"""
from sqlalchemy import Column, DateTime, String
from sqlalchemy.orm import declarative_mixin

@declarative_mixin
class StatusChange:
    status_change_date = Column(DateTime, nullable=True)
    status_change_user_login = Column(String, nullable=True)
    status_change_user_workspace = Column(String, nullable=True)
