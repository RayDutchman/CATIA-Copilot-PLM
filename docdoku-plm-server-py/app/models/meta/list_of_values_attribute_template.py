"""ListOfValuesAttributeTemplate ORM 模型。"""
from sqlalchemy import Column, String, ForeignKey
from app.core.database import Base

class ListOfValuesAttributeTemplate(Base):
    __tablename__ = "listofvaluesattributetemplate"
    id = Column(String, primary_key=True)
    name = Column(String)
