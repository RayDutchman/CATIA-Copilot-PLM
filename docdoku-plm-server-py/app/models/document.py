# app/models/document.py
from typing import Optional, List
from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime, Text,
    ForeignKey, ForeignKeyConstraint, Table
)
from sqlalchemy.orm import relationship, Mapped
from app.core.database import Base

document_iteration_binres = Table(
    "documentiteration_binres", Base.metadata,
    Column("workspace_id", String, primary_key=True),
    Column("documentmaster_id", String, primary_key=True),
    Column("documentrevision_version", String, primary_key=True),
    Column("iteration", Integer, primary_key=True),
    Column("attachedfile_fullname", String,
           ForeignKey("binaryresource.fullname"), primary_key=True),
    ForeignKeyConstraint(
        ["workspace_id", "documentmaster_id", "documentrevision_version", "iteration"],
        ["documentiteration.workspace_id", "documentiteration.documentmaster_id",
         "documentiteration.documentrevision_version", "documentiteration.iteration"],
    ),
)

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

class Folder(Base):
    __tablename__ = "folder"
    completepath = Column("completepath", String, primary_key=True)
    parentfolder_completepath = Column("parentfolder_completepath", String,
                                       ForeignKey("folder.completepath"))

class DocumentMaster(Base):
    __tablename__ = "documentmaster"
    id = Column(String, primary_key=True)
    workspace_id = Column(String, primary_key=True)
    type = Column(String)
    creation_date = Column("creationdate", DateTime)
    attributes_locked = Column("attributeslocked", Boolean, default=False)
    author_workspace_id = Column(String)
    author_login = Column(String)

    revisions: Mapped[List["DocumentRevision"]] = relationship(
        "DocumentRevision",
        foreign_keys="[DocumentRevision.workspace_id, DocumentRevision.documentmaster_id]",
        primaryjoin=(
            "and_(DocumentMaster.workspace_id==DocumentRevision.workspace_id,"
            "DocumentMaster.id==DocumentRevision.documentmaster_id)"),
        order_by="DocumentRevision.version", back_populates="document_master",
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
        primaryjoin=("and_(DocumentRevision.workspace_id==DocumentMaster.workspace_id,"
                     "DocumentRevision.documentmaster_id==DocumentMaster.id)"),
        back_populates="revisions")
    iterations: Mapped[List["DocumentIteration"]] = relationship(
        "DocumentIteration",
        foreign_keys=("DocumentIteration.workspace_id,DocumentIteration.documentmaster_id,"
                      "DocumentIteration.documentrevision_version"),
        primaryjoin=("and_(DocumentRevision.workspace_id==DocumentIteration.workspace_id,"
                     "DocumentRevision.documentmaster_id==DocumentIteration.documentmaster_id,"
                     "DocumentRevision.version==DocumentIteration.documentrevision_version)"),
        order_by="DocumentIteration.iteration", back_populates="revision",
        cascade="all, delete-orphan")

    @property
    def last_iteration(self):
        return self.iterations[-1] if self.iterations else None

    @property
    def last_iteration_number(self) -> int:
        return self.iterations[-1].iteration if self.iterations else 0

class DocumentIteration(Base):
    __tablename__ = "documentiteration"
    workspace_id = Column(String, primary_key=True)
    documentmaster_id = Column(String, primary_key=True)
    documentrevision_version = Column(String, primary_key=True)
    iteration = Column(Integer, primary_key=True)
    revision_note = Column("revisionnote", String)
    creation_date = Column("creationdate", DateTime)
    modification_date = Column("modificationdate", DateTime)
    check_in_date = Column("checkindate", DateTime)
    author_workspace_id = Column(String)
    author_login = Column(String)

    revision: Mapped["DocumentRevision"] = relationship(
        "DocumentRevision",
        foreign_keys=[workspace_id, documentmaster_id, documentrevision_version],
        primaryjoin=("and_(DocumentIteration.workspace_id==DocumentRevision.workspace_id,"
                     "DocumentIteration.documentmaster_id==DocumentRevision.documentmaster_id,"
                     "DocumentIteration.documentrevision_version==DocumentRevision.version)"),
        back_populates="iterations")

class DocumentMasterTemplate(Base):
    __tablename__ = "documentmastertemplate"
    workspace_id = Column(String, primary_key=True)
    id = Column(String, primary_key=True)
    document_type = Column("documenttype", String)
    mask = Column(String)
    id_generated = Column("idgenerated", Boolean, default=False)
    attributes_locked = Column("attributeslocked", Boolean, default=False)
    creation_date = Column("creationdate", DateTime)
    modification_date = Column("modificationdate", DateTime)
    author_workspace_id = Column(String)
    author_login = Column(String)
    workflowmodel_id = Column(String)
    acl_id = Column(Integer)
