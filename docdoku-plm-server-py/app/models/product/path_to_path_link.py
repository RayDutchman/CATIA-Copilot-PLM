"""PathToPathLink ORM 模型，映射 pathtopathlink 表。"""
from sqlalchemy import Column, String, Integer, Float
from app.core.database import Base


class PathToPathLink(Base):
    __tablename__ = "pathtopathlink"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String)
    source_path = Column("sourcepath", String)
    target_path = Column("targetpath", String)
    description = Column(String)
