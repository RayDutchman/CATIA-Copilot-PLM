"""InstancePartNumberAttribute ORM 模型。"""
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class InstancePartNumberAttribute(Base):
    __tablename__ = "instancepartnumberattribute"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    partnumber_workspace_id = Column(String)
    partnumber_partnumber = Column(String)
