"""Subscription ORM 抽象基类。"""
from sqlalchemy import Column, String
from app.core.database import Base

class Subscription(Base):
    __tablename__ = "subscription"
    subscriber_login = Column(String, primary_key=True)
    subscriber_workspace_id = Column(String, primary_key=True)
    dtype = Column(String)
    __mapper_args__ = {"polymorphic_on": dtype}
