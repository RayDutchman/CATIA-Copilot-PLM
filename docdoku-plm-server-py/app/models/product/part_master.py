"""PartMaster ORM 模型，映射 partmaster 表。零件主数据（跨版本共享的信息）。"""
from typing import Optional, List
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship, Mapped
from app.core.database import Base


class PartMaster(Base):
    __tablename__ = "partmaster"

    workspace_id = Column(String, primary_key=True)
    number = Column("partnumber", String, primary_key=True)
    name = Column(String)
    type = Column(String)
    standard_part = Column("standardpart", Boolean, default=False)
    attributes_locked = Column("attributeslocked", Boolean, default=False)
    creation_date = Column("creationdate", DateTime)
    author_workspace_id = Column(String)
    author_login = Column(String)

    revisions: Mapped[List["PartRevision"]] = relationship(
        "PartRevision",
        foreign_keys="[PartRevision.workspace_id, PartRevision.partmaster_partnumber]",
        primaryjoin=(
            "and_(PartMaster.workspace_id==PartRevision.workspace_id,"
            "PartMaster.number==PartRevision.partmaster_partnumber)"
        ),
        order_by="PartRevision.version",
        back_populates="part_master",
    )

    @property
    def last_revision(self) -> Optional["PartRevision"]:
        if not self.revisions:
            return None
        return self.revisions[-1]
