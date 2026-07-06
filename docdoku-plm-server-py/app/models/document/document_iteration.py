"""DocumentIteration ORM 模型，映射 documentiteration 表。"""
from typing import List
from sqlalchemy import (
    Column, String, Integer, DateTime,
    ForeignKey, ForeignKeyConstraint, Table,
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
        primaryjoin=(
            "and_(DocumentIteration.workspace_id==DocumentRevision.workspace_id,"
            "DocumentIteration.documentmaster_id==DocumentRevision.documentmaster_id,"
            "DocumentIteration.documentrevision_version==DocumentRevision.version)"),
        back_populates="iterations",
    )
