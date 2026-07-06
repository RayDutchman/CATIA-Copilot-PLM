"""DefaultAttributeTemplate ORM 模型。"""
from sqlalchemy import Column, String, Integer, ForeignKey
from app.core.database import Base

class DefaultAttributeTemplate(Base):
    __tablename__ = "defaultattributetemplate"
    id = Column(Integer, primary_key=True, autoincrement=True)
    attribute_name = Column("attributename", String)
    attribute_type = Column("attributetype", Integer)
    attribute_value = Column("attributevalue", String)
