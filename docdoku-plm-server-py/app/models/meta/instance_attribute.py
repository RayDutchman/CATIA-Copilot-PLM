"""InstanceAttribute 抽象基类。"""
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime
from app.core.database import Base

class InstanceAttribute(Base):
    __tablename__ = "instanceattribute"
    id = Column(Integer, primary_key=True, autoincrement=True)
    dtype = Column(String)
    name = Column(String, nullable=False)
    mandatory = Column(Boolean, default=False)
    locked = Column(Boolean, default=False)
    stringvalue = Column(String, nullable=True)
    booleandefaultvalue = Column(Boolean, name="booleanvalue", nullable=True)
    datevalue = Column(DateTime, nullable=True)
    floatvalue = Column(Float, nullable=True)
    integervalue = Column(Integer, nullable=True)
    urlvalue = Column(String, nullable=True)
    __mapper_args__ = {"polymorphic_on": dtype}
