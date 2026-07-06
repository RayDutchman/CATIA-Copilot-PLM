"""PartSubstituteLink ORM 模型，映射 partsubstitutelink 表。替代件链接。"""
from typing import Optional, List
from sqlalchemy import (
    Column, String, Integer, Float, ForeignKey, Table,
)
from sqlalchemy.orm import relationship, Mapped
from app.core.database import Base


# 替代件链接的 CAD 实例关联表
substitute_link_cadinstances = Table(
    "partsubstitutelink_cadinstance", Base.metadata,
    Column("partsubstitutelink_id", Integer, ForeignKey("partsubstitutelink.id"), primary_key=True),
    Column("cadinstance_id", Integer, ForeignKey("cadinstance.id"), primary_key=True),
    Column("cadinstance_order", Integer),
)


class PartSubstituteLink(Base):
    __tablename__ = "partsubstitutelink"

    id = Column(Integer, primary_key=True, autoincrement=True)
    amount = Column(Float, default=1.0)
    comment = Column("commentdata", String)
    reference_description = Column("referencedescription", String)
    unit = Column(String)
    substitute_workspace_id = Column(String)
    substitute_partnumber = Column(String)

    substitute: Mapped[Optional["PartMaster"]] = relationship(
        "PartMaster",
        foreign_keys=[substitute_workspace_id, substitute_partnumber],
        primaryjoin=(
            "and_(PartSubstituteLink.substitute_workspace_id==PartMaster.workspace_id,"
            "PartSubstituteLink.substitute_partnumber==PartMaster.number)"
        ),
    )
    cad_instances: Mapped[List["CADInstance"]] = relationship(
        "CADInstance",
        secondary=substitute_link_cadinstances,
    )
