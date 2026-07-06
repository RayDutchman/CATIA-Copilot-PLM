"""ProductConfiguration ORM 模型，映射 productconfiguration 表。"""
from sqlalchemy import Column, String, Integer, DateTime, Text
from app.core.database import Base


class ProductConfiguration(Base):
    __tablename__ = "productconfiguration"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    creation_date = Column("creationdate", DateTime)
    author_workspace_id = Column(String)
    author_login = Column(String)
    configurationitem_id = Column(String)
    configurationitem_workspace_id = Column(String)
    acl_id = Column(Integer)
