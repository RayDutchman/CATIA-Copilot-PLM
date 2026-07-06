"""CADInstance ORM 模型，映射 cadinstance 表。存储装配位置（欧拉角或旋转矩阵）。"""
from sqlalchemy import Column, Integer, Float, String
from app.core.database import Base


class CADInstance(Base):
    __tablename__ = "cadinstance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rotation_type = Column("rotationtype", String)
    rx = Column(Float)
    ry = Column(Float)
    rz = Column(Float)
    tx = Column(Float)
    ty = Column(Float)
    tz = Column(Float)
    m00 = Column(Float); m01 = Column(Float); m02 = Column(Float)
    m10 = Column(Float); m11 = Column(Float); m12 = Column(Float)
    m20 = Column(Float); m21 = Column(Float); m22 = Column(Float)
