"""PathDataIteration ORM 模型。"""
from sqlalchemy import Column, String, Integer, DateTime
from app.core.database import Base

class PathDataIteration(Base):
    __tablename__ = "pathdataiteration"
    id = Column(Integer, primary_key=True, autoincrement=True)
    iteration = Column(Integer)
    iteration_note = Column("iterationnote", String)
    creation_date = Column("creationdate", DateTime)
    modification_date = Column("modificationdate", DateTime)
    author_workspace_id = Column(String)
    author_login = Column(String)
    pathdatamaster_id = Column(Integer)
