"""ResolvedCollection ORM 模型。"""
from sqlalchemy import Column, Integer
from app.core.database import Base

class ResolvedCollection(Base):
    __tablename__ = "resolvedcollection"
    id = Column(Integer, primary_key=True, autoincrement=True)
