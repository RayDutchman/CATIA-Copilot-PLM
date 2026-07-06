"""PartCollection ORM 模型。"""
from sqlalchemy import Column, Integer
from app.core.database import Base

class PartCollection(Base):
    __tablename__ = "partcollection"
    id = Column(Integer, primary_key=True, autoincrement=True)
