"""DocumentMaster ORM 模型，映射 documentmaster 表。"""
from typing import List, Optional
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.orm import relationship, Mapped
from app.core.database import Base


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
        order_by="DocumentRevision.version",
        back_populates="document_master",
    )
