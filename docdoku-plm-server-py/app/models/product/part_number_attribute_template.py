"""PartNumberAttributeTemplate ORM 模型。"""
from sqlalchemy import Column, String, Integer
from app.core.database import Base


class PartNumberAttributeTemplate(Base):
    __tablename__ = "partnumberattributetemplate"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    partnumberattributetype = Column(String)
