"""Conversion ORM 模型，映射 conversion 表。记录 CAD 转换任务状态。"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKeyConstraint
from app.core.database import Base


class Conversion(Base):
    __tablename__ = "conversion"

    workspace_id = Column(String, primary_key=True)
    partmaster_partnumber = Column(String, primary_key=True)
    partrevision_version = Column(String, primary_key=True)
    iteration = Column(Integer, primary_key=True)
    pending = Column(Boolean, default=True)
    succeed = Column(Boolean, default=False)
    start_date = Column("startdate", DateTime)
    end_date = Column("enddate", DateTime)

    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "partmaster_partnumber", "partrevision_version", "iteration"],
            ["partiteration.workspace_id", "partiteration.partmaster_partnumber",
             "partiteration.partrevision_version", "partiteration.iteration"],
        ),
    )
