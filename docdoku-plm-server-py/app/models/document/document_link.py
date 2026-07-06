"""DocumentLink ORM 模型，映射 documentlink 表。"""
from typing import Optional
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship, Mapped
from app.core.database import Base


class DocumentLink(Base):
    __tablename__ = "documentlink"

    id = Column(Integer, primary_key=True, autoincrement=True)
    comment = Column("commentdata", String)
    target_documentmaster_id = Column("target_documentmaster_id", String)
    target_docrevision_version = Column("target_docrevision_version", String)
    target_workspace_id = Column("target_workspace_id", String)

    target_document: Mapped[Optional["DocumentRevision"]] = relationship(
        "DocumentRevision",
        foreign_keys=[target_workspace_id, target_documentmaster_id, target_docrevision_version],
        primaryjoin=(
            "and_(DocumentLink.target_workspace_id==DocumentRevision.workspace_id,"
            "DocumentLink.target_documentmaster_id==DocumentRevision.documentmaster_id,"
            "DocumentLink.target_docrevision_version==DocumentRevision.version)"
        ),
    )
