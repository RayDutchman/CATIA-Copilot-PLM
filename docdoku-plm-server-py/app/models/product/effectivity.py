"""Effectivity ORM 抽象基类，映射 effectivity 表（SINGLE_TABLE 继承）。"""
from sqlalchemy import Column, String, Integer, DateTime
from app.core.database import Base


class Effectivity(Base):
    __tablename__ = "effectivity"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dtype = Column(String)
    name = Column(String)
    description = Column(String)
    start_date = Column("startdate", DateTime, nullable=True)
    end_date = Column("enddate", DateTime, nullable=True)
    start_number = Column("startnumber", String, nullable=True)
    end_number = Column("endnumber", String, nullable=True)
    start_lot = Column("startlotid", String, nullable=True)
    end_lot = Column("endlotid", String, nullable=True)
    configurationitem_id = Column(String, nullable=True)
    configurationitem_workspace_id = Column(String, nullable=True)

    __mapper_args__ = {"polymorphic_on": dtype}
