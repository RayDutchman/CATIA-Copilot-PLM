"""ListOfValues ORM 模型。"""
from sqlalchemy import Column, String, ForeignKey
from app.core.database import Base

class ListOfValues(Base):
    __tablename__ = "listofvalues"
    name = Column(String, primary_key=True)
    workspace_id = Column(String, primary_key=True)
