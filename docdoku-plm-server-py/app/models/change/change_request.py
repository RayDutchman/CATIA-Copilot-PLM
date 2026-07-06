"""ChangeRequest ORM 模型，映射 changerequest 表。"""
from typing import List
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Table
from sqlalchemy.orm import relationship, Mapped
from app.core.database import Base


change_request_tags = Table(
    "changerequest_tag", Base.metadata,
    Column("changerequest_id", Integer, ForeignKey("changerequest.id"), primary_key=True),
    Column("tag_workspace_id", String, primary_key=True),
    Column("tag_label", String, primary_key=True),
)


class ChangeRequest(Base):
    __tablename__ = "changerequest"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(Text)
    category = Column(Integer)
    priority = Column(Integer)
    creation_date = Column("creationdate", DateTime)
    milestone_id = Column(Integer)
    assignee_workspace_id = Column(String)
    assignee_login = Column(String)
    author_workspace_id = Column(String)
    author_login = Column(String)
    workspace_id = Column(String)
    acl_id = Column(Integer)

    tags: Mapped[List["Tag"]] = relationship(
        "Tag",
        secondary=change_request_tags,
        primaryjoin=lambda: ChangeRequest.id == change_request_tags.c.changerequest_id,
        secondaryjoin=lambda: (
            (Tag.workspace_id == change_request_tags.c.tag_workspace_id)
            & (Tag.label == change_request_tags.c.tag_label)
        ),
    )


from app.models.part import Tag  # noqa: E402
