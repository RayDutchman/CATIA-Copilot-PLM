"""ProductBaseline ORM 模型，映射 productbaseline 表。"""
from sqlalchemy import Column, String, Integer, DateTime, Text
from app.core.database import Base


class ProductBaseline(Base):
    __tablename__ = "productbaseline"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    creation_date = Column("creationdate", DateTime)
    type = Column(Integer)
    author_workspace_id = Column(String)
    author_login = Column(String)
    configurationitem_id = Column(String)
    configurationitem_workspace_id = Column(String)
    documentcollection_id = Column(Integer)
    partcollection_id = Column(Integer)
