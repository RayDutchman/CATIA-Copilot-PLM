"""Layer ORM 模型，映射 layer 表。"""
from sqlalchemy import Column, String, Integer, DateTime
from app.core.database import Base


class Layer(Base):
    __tablename__ = "layer"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    color = Column(String)
    creation_date = Column("creationdate", DateTime)
    author_workspace_id = Column(String)
    author_login = Column(String)
    configurationitem_id = Column(String)
    configurationitem_workspace_id = Column(String)
