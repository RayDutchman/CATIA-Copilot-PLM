"""PartAlternateLink 嵌入式模型，映射 partmaster_alternate 集合表。"""
from typing import Optional
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship, Mapped
from app.core.database import Base


class PartAlternateLink(Base):
    __tablename__ = "partmaster_alternate"

    partmaster_workspace_id = Column(String, ForeignKey("partmaster.workspace_id"), primary_key=True)
    partmaster_partnumber = Column(String, ForeignKey("partmaster.partnumber"), primary_key=True)
    alternate_order = Column(String, primary_key=True)
    reference_description = Column("referencedescription", String)
    comment = Column("commentdata", String)
    alternate_workspace_id = Column(String)
    alternate_partnumber = Column(String)

    alternate: Mapped[Optional["PartMaster"]] = relationship(
        "PartMaster",
        foreign_keys=[alternate_workspace_id, alternate_partnumber],
        primaryjoin=(
            "and_(PartAlternateLink.alternate_workspace_id==PartMaster.workspace_id,"
            "PartAlternateLink.alternate_partnumber==PartMaster.number)"
        ),
    )
