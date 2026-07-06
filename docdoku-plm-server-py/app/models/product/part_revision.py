"""PartRevision ORM 模型，映射 partrevision 表。零件的一个版本（A/B/C...）。"""
from typing import Optional, List
from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime, Text, ForeignKeyConstraint, Table,
)
from sqlalchemy.orm import relationship, Mapped
from app.core.database import Base


# partrevision → 标签（M:N）
part_revision_tags = Table(
    "partrevision_tag", Base.metadata,
    Column("partmaster_workspace_id", String, primary_key=True),
    Column("partmaster_partnumber", String, primary_key=True),
    Column("partrevision_version", String, primary_key=True),
    Column("tag_workspace_id", String, primary_key=True),
    Column("tag_label", String, primary_key=True),
    ForeignKeyConstraint(
        ["partmaster_workspace_id", "partmaster_partnumber", "partrevision_version"],
        ["partrevision.workspace_id", "partrevision.partmaster_partnumber",
         "partrevision.version"],
    ),
)


class PartRevision(Base):
    __tablename__ = "partrevision"

    workspace_id = Column(String, primary_key=True)
    partmaster_partnumber = Column(String, primary_key=True)
    version = Column(String, primary_key=True)

    description = Column(Text)
    status = Column(Integer, default=0)
    public_shared = Column("publicshared", Boolean, default=False)
    creation_date = Column("creationdate", DateTime)
    check_out_date = Column("checkoutdate", DateTime)
    release_date = Column("release_date", DateTime)
    obsolete_date = Column("obsolete_date", DateTime)

    author_workspace_id = Column(String)
    author_login = Column(String)
    checkout_user_workspace_id = Column("checkoutuser_workspace_id", String)
    checkout_user_login = Column("checkoutuser_login", String)
    release_user_workspace = Column(String)
    release_user_login = Column(String)
    obsolete_user_workspace = Column(String)
    obsolete_user_login = Column(String)

    acl_id = Column(Integer)
    workflow_id = Column(Integer)

    part_master: Mapped["PartMaster"] = relationship(
        "PartMaster",
        foreign_keys=[workspace_id, partmaster_partnumber],
        primaryjoin=(
            "and_(PartRevision.workspace_id==PartMaster.workspace_id,"
            "PartRevision.partmaster_partnumber==PartMaster.number)"
        ),
        back_populates="revisions",
    )
    iterations: Mapped[List["PartIteration"]] = relationship(
        "PartIteration",
        foreign_keys=(
            "PartIteration.workspace_id, PartIteration.partmaster_partnumber,"
            "PartIteration.partrevision_version"
        ),
        primaryjoin=(
            "and_(PartRevision.workspace_id==PartIteration.workspace_id,"
            "PartRevision.partmaster_partnumber==PartIteration.partmaster_partnumber,"
            "PartRevision.version==PartIteration.partrevision_version)"
        ),
        order_by="PartIteration.iteration",
        back_populates="revision",
        cascade="all, delete-orphan",
    )
    tags: Mapped[List["Tag"]] = relationship(
        "Tag",
        secondary=part_revision_tags,
        primaryjoin=lambda: (
            (PartRevision.workspace_id == part_revision_tags.c.partmaster_workspace_id)
            & (PartRevision.partmaster_partnumber == part_revision_tags.c.partmaster_partnumber)
            & (PartRevision.version == part_revision_tags.c.partrevision_version)
        ),
        secondaryjoin="and_(foreign(Tag.workspace_id)==remote(part_revision_tags.c.tag_workspace_id), foreign(Tag.label)==remote(part_revision_tags.c.tag_label))",
    )

    @property
    def last_iteration(self) -> Optional["PartIteration"]:
        if not self.iterations:
            return None
        return self.iterations[-1]

    @property
    def last_iteration_number(self) -> int:
        if not self.iterations:
            return 0
        return self.iterations[-1].iteration

    @property
    def status_label(self) -> str:
        return {0: "WIP", 1: "RELEASED", 2: "OBSOLETE"}.get(self.status, "WIP")

    @property
    def is_last_revision(self) -> bool:
        master = self.part_master
        if master is None:
            return False
        return master.last_revision is self


from app.models.part import Tag  # noqa: E402
