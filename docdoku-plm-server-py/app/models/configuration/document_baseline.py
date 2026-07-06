"""DocumentBaseline ORM 模型。"""
from sqlalchemy import Column, String, Integer, DateTime, Text
from app.core.database import Base

class DocumentBaseline(Base):
    __tablename__ = "documentbaseline"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    creation_date = Column("creationdate", DateTime)
    type = Column(Integer)
    author_workspace_id = Column(String)
    author_login = Column(String)
    documentcollection_id = Column(Integer)
