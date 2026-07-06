"""ConfigurationItem ORM 模型，映射 configurationitem 表。产品配置项。"""
from typing import Optional
from sqlalchemy import (
    Column, String, DateTime, Text, ForeignKey,
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
