"""Account ORM 模型，映射 account 表。"""
from sqlalchemy import Column, String, Boolean
from app.core.database import Base


class Account(Base):
    __tablename__ = "account"

    login = Column(String, primary_key=True)
    email = Column(String)
    name = Column(String)
    language = Column(String)
    timezone = Column(String)
    enabled = Column(Boolean, default=True)
