"""PathDataMaster ORM 模型。

对齐数据库 pathdatamaster 表（实际仅有 id/path 两列）。
"""
from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship
from app.core.database import Base


class PathDataMaster(Base):
    __tablename__ = "pathdatamaster"

    # 主键，自增序列
    id = Column(Integer, primary_key=True, autoincrement=True)
    # 路径字符串，如 "-1-u2-u5"
    path = Column(String(255))

    # 关联迭代列表（一对多，外键在 pathdataiteration.pathdatamaster_id）
    iterations = relationship(
        "PathDataIteration",
        back_populates="master",
        order_by="PathDataIteration.iteration",
        cascade="all, delete-orphan",
    )
