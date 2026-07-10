"""PathDataIteration ORM 模型。

对齐数据库 pathdataiteration 表：
  复合主键 (iteration, pathdatamaster_id)
  字段：dateiteration, iterationnote
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class PathDataIteration(Base):
    __tablename__ = "pathdataiteration"

    # 复合主键（对齐 DB：pathdataiteration_pkey PRIMARY KEY (iteration, pathdatamaster_id)）
    iteration = Column(Integer, primary_key=True)
    pathdatamaster_id = Column(
        Integer,
        ForeignKey("pathdatamaster.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # 迭代时间戳
    dateiteration = Column(DateTime, default=datetime.utcnow)
    # 迭代备注
    iterationnote = Column(Text)

    # 反向关联到 PathDataMaster
    master = relationship("PathDataMaster", back_populates="iterations")
