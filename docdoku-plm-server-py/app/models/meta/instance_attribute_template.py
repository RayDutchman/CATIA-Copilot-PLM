"""InstanceAttributeTemplate ORM 基类。"""
from sqlalchemy import Column, String, Integer, Boolean
from app.core.database import Base

class InstanceAttributeTemplate(Base):
    __tablename__ = "instanceattributetemplate"
    id = Column(Integer, primary_key=True, autoincrement=True)
    dtype = Column(String)
    name = Column(String, nullable=False)
    mandatory = Column(Boolean, default=False)
    locked = Column(Boolean, default=False)
    attributetype = Column(Integer)
    __mapper_args__ = {"polymorphic_on": dtype}
