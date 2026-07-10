"""Import ORM 模型，映射 import 表。"""
from sqlalchemy import Column, String, Boolean, DateTime
from app.core.database import Base


class Import(Base):
    __tablename__ = "import"

    id = Column(String, primary_key=True)
    end_date = Column("enddate", DateTime)
    file_name = Column("filename", String)
    pending = Column(Boolean)
    start_date = Column("startdate", DateTime)
    succeed = Column(Boolean)
    user_login = Column(String)
    user_workspace_id = Column(String)
