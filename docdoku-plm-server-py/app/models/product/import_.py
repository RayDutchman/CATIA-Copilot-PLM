"""Import ORM 模型，映射 import 表。"""
from sqlalchemy import Column, String, Integer, DateTime
from app.core.database import Base


class Import(Base):
    __tablename__ = "import"

    id = Column(String, primary_key=True)
    user_login = Column(String)
    user_workspace_id = Column(String)
    creation_date = Column("creationdate", DateTime)
    file_name = Column("filename", String)
    pending = Column(Integer)
    succeed = Column(Integer)
    result_path = Column("resultpath", String)
    workspace_id = Column(String)
