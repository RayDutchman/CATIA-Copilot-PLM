"""PartMasterTemplate ORM 模型，映射 partmastertemplate 表。"""
from typing import Optional, List
from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, ForeignKey,
)
from sqlalchemy.orm import relationship, Mapped
from app.core.database import Base
from app.models.part import BinaryResource


class PartMasterTemplate(Base):
    __tablename__ = "partmastertemplate"

    id = Column(String, primary_key=True)
    workspace_id = Column(String, primary_key=True)
    mask = Column(String)
    id_generated = Column("idgenerated", Boolean, default=False)
    part_type = Column("parttype", String)
    attributes_locked = Column("attributeslocked", Boolean, default=False)
    author_login = Column(String)
    author_workspace_id = Column(String)
    creation_date = Column("creationdate", DateTime)
    modification_date = Column("modificationdate", DateTime)
    acl_id = Column(Integer, nullable=True)
    workflowmodel_id = Column(String, nullable=True)
