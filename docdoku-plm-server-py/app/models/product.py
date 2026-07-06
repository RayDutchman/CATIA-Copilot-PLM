"""ORM: configurationitem → productbaseline/productconfiguration/productinstance。"""
from typing import Optional
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Text, ForeignKey
)
from sqlalchemy.orm import relationship, Mapped
from app.core.database import Base


class ConfigurationItem(Base):
    __tablename__ = "configurationitem"
    workspace_id = Column(String, primary_key=True)
    id = Column(String, primary_key=True)
    description = Column(Text)
    creation_date = Column("creationdate", DateTime)
    partmaster_workspace_id = Column(String)
    partmaster_partnumber = Column(String)
    author_workspace_id = Column(String)
    author_login = Column(String)

    part_master: Mapped[Optional["PartMaster"]] = relationship(
        "PartMaster",
        foreign_keys=[partmaster_workspace_id, partmaster_partnumber],
        primaryjoin=(
            "and_(ConfigurationItem.partmaster_workspace_id==PartMaster.workspace_id,"
            "ConfigurationItem.partmaster_partnumber==PartMaster.number)"
        ),
    )

from app.models.part import PartMaster  # noqa: E402


class ProductBaseline(Base):
    __tablename__ = "productbaseline"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    creation_date = Column("creationdate", DateTime)
    type = Column(Integer)
    author_workspace_id = Column(String)
    author_login = Column(String)
    configurationitem_id = Column(String)
    configurationitem_workspace_id = Column(String)
    documentcollection_id = Column(Integer)
    partcollection_id = Column(Integer)


class ProductConfiguration(Base):
    __tablename__ = "productconfiguration"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    creation_date = Column("creationdate", DateTime)
    author_workspace_id = Column(String)
    author_login = Column(String)
    configurationitem_id = Column(String)
    configurationitem_workspace_id = Column(String)
    acl_id = Column(Integer)


class ProductInstanceMaster(Base):
    __tablename__ = "productinstancemaster"
    serialnumber = Column("serialnumber", String, primary_key=True)
    workspace_id = Column(String, primary_key=True)
    configurationitem_id = Column(String, primary_key=True)
    acl_id = Column(Integer)


class ProductInstanceIteration(Base):
    __tablename__ = "productinstanceiteration"
    workspace_id = Column(String, primary_key=True)
    configurationitem_id = Column(String, primary_key=True)
    prdinstancemaster_serialnumber = Column("prdinstancemaster_serialnumber", String, primary_key=True)
    iteration = Column(Integer, primary_key=True)
    creation_date = Column("creationdate", DateTime)
    modification_date = Column("modificationdate", DateTime)
    iteration_note = Column("iterationnote", String)
    productbaseline_id = Column(Integer)
    author_workspace_id = Column(String)
    author_login = Column(String)
    documentcollection_id = Column(Integer)
    partcollection_id = Column(Integer)


class Layer(Base):
    __tablename__ = "layer"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    color = Column(String)
    creation_date = Column("creationdate", DateTime)
    author_workspace_id = Column(String)
    author_login = Column(String)
    configurationitem_id = Column(String)
    configurationitem_workspace_id = Column(String)


class Marker(Base):
    __tablename__ = "marker"
    id = Column(Integer, primary_key=True, autoincrement=True)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    z = Column(Float, nullable=False)
    title = Column(String)
    description = Column(Text)
    creation_date = Column("creationdate", DateTime)
    author_workspace_id = Column(String)
    author_login = Column(String)
