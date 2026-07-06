"""DocumentRevision ORM 模型，映射 documentrevision 表。"""
from typing import List, Optional
from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime, Text,
    ForeignKeyConstraint, Table,
)
from sqlalchemy.orm import relationship, Mapped
from app.core.database import Base


document_revision_tags = Table(
    "documentrevision_tag", Base.metadata,
    Column("documentmaster_workspace_id", String, primary_key=True),
    Column("documentmaster_id", String, primary_key=True),
    Column("documentrevision_version", String, primary_key=True),
    Column("tag_workspace_id", String, primary_key=True),
    Column("tag_label", String, primary_key=True),
    ForeignKeyConstraint(
        ["documentmaster_workspace_id", "documentmaster_id", "documentrevision_version"],
        ["documentrevision.workspace_id", "documentrevision.documentmaster_id",
         "documentrevision.version"],
    ),
)


class DocumentRevision(Base):
    __tablename__ = "documentrevision"

    workspace_id = Column(String, primary_key=True)
    documentmaster_id = Column(String, primary_key=True)
    version = Column(String, primary_key=True)

    title = Column(String)
    description = Column(Text)
    status = Column(Integer, default=0)
    public_shared = Column("publicshared", Boolean, default=False)
    creation_date = Column("creationdate", DateTime)
    check_out_date = Column("checkoutdate", DateTime)
    release_date = Column("release_date", DateTime)
    obsolete_date = Column("obsolete_date", DateTime)
    location_completepath = Column("location_completepath", String)
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

    document_master: Mapped["DocumentMaster"] = relationship(
        "DocumentMaster",
        foreign_keys=[workspace_id, documentmaster_id],
        primaryjoin=(
            "and_(DocumentRevision.workspace_id==DocumentMaster.workspace_id,"
            "DocumentRevision.documentmaster_id==DocumentMaster.id)"),
        back_populates="revisions",
    )
    iterations: Mapped[List["DocumentIteration"]] = relationship(
        "DocumentIteration",
        foreign_keys=(
            "DocumentIteration.workspace_id,DocumentIteration.documentmaster_id,"
            "DocumentIteration.documentrevision_version"
        ),
        primaryjoin=(
            "and_(DocumentRevision.workspace_id==DocumentIteration.workspace_id,"
            "DocumentRevision.documentmaster_id==DocumentIteration.documentmaster_id,"
            "DocumentRevision.version==DocumentIteration.documentrevision_version)"),
        order_by="DocumentIteration.iteration",
        back_populates="revision",
        cascade="all, delete-orphan",
    )

    @property
    def last_iteration(self):
        return self.iterations[-1] if self.iterations else None

    @property
    def last_iteration_number(self) -> int:
        return self.iterations[-1].iteration if self.iterations else 0
