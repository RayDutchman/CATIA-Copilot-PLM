"""Credential ORM 模型。"""
from sqlalchemy import Column, String, ForeignKey
from app.core.database import Base

class Credential(Base):
    __tablename__ = "credential"
    login = Column(String, ForeignKey("account.login"), primary_key=True)
    password = Column(String)
