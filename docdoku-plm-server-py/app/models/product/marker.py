"""Marker ORM 模型，映射 marker 表。"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Text
from app.core.database import Base


class Marker(Base):
    __tablename__ = "marker"

    id = Column(Integer, primary_key=True, autoincrement=True)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    z = Column(Float, nullable=False)
    title = Column(String)
    description = Column(Text)
    creation_date = Column("creationdate", DateTime)
    author_workspace_id = Column(String)
    author_login = Column(String)
