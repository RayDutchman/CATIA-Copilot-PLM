"""BinaryResource ORM 模型，映射 binaryresource 表。存储文件元数据。"""
from sqlalchemy import Column, String, BigInteger, DateTime, Integer, Float
from app.core.database import Base


class BinaryResource(Base):
    __tablename__ = "binaryresource"

    full_name = Column("fullname", String, primary_key=True)
    dtype = Column(String)
    content_length = Column("contentlength", BigInteger)
    last_modified = Column("lastmodified", DateTime)
    quality = Column(Integer)
    x_min = Column("x_min", Float)
    x_max = Column("x_max", Float)
    y_min = Column("y_min", Float)
    y_max = Column("y_max", Float)
    z_min = Column("z_min", Float)
    z_max = Column("z_max", Float)
