"""PathDataMaster ORM 模型。"""
from sqlalchemy import Column, String, Integer, DateTime
from app.core.database import Base

class PathDataMaster(Base):
    __tablename__ = "pathdatamaster"
    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(String)
    creation_date = Column("creationdate", DateTime)
    author_workspace_id = Column(String)
    author_login = Column(String)
