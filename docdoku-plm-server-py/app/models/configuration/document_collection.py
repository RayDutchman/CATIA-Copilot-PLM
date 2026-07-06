"""DocumentCollection ORM 模型。"""
from sqlalchemy import Column, Integer, ForeignKey
from app.core.database import Base

class DocumentCollection(Base):
    __tablename__ = "documentcollection"
    id = Column(Integer, primary_key=True, autoincrement=True)
