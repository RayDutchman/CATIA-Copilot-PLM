"""PartUsageLink ORM 模型，映射 partusagelink 表。装配子件链接。"""
from typing import Optional, List
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, ForeignKey, Table,
)
from sqlalchemy.orm import relationship, Mapped
from app.core.database import Base


# 子件链接的 CAD 实例关联表
usage_link_cadinstances = Table(
    "partusagelink_cadinstance", Base.metadata,
    Column("partusagelink_id", Integer, ForeignKey("partusagelink.id"), primary_key=True),
    Column("cadinstance_id", Integer, ForeignKey("cadinstance.id"), primary_key=True),
    Column("cadinstance_order", Integer),
)


class PartUsageLink(Base):
    __tablename__ = "partusagelink"

    id = Column(Integer, primary_key=True, autoincrement=True)
    amount = Column(Float, default=1.0)
    comment = Column("commentdata", String)
    optional = Column(Boolean, default=False)
    reference_description = Column("referencedescription", String)
    unit = Column(String)
    component_workspace_id = Column(String)
    component_partnumber = Column(String)

    component: Mapped[Optional["PartMaster"]] = relationship(
        "PartMaster",
        foreign_keys=[component_workspace_id, component_partnumber],
        primaryjoin=(
            "and_(PartUsageLink.component_workspace_id==PartMaster.workspace_id,"
            "PartUsageLink.component_partnumber==PartMaster.number)"
        ),
    )
    cad_instances: Mapped[List["CADInstance"]] = relationship(
        "CADInstance",
        secondary=usage_link_cadinstances,
    )
