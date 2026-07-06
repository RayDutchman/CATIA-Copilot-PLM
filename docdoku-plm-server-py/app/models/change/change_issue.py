"""ChangeIssue ORM 模型，映射 changeissue 表。"""
from typing import List
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Table
from sqlalchemy.orm import relationship, Mapped
from app.core.database import Base


change_issue_tags = Table(
    "changeissue_tag", Base.metadata,
    Column("changeissue_id", Integer, ForeignKey("changeissue.id"), primary_key=True),
    Column("tag_workspace_id", String, primary_key=True),
    Column("tag_label", String, primary_key=True),
)


class ChangeIssue(Base):
    __tablename__ = "changeissue"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(Text)
    initiator = Column(String)
    category = Column(Integer)
    priority = Column(Integer)
    creation_date = Column("creationdate", DateTime)
    assignee_workspace_id = Column(String)
    assignee_login = Column(String)
    author_workspace_id = Column(String)
    author_login = Column(String)
    workspace_id = Column(String)
    acl_id = Column(Integer)

    tags: Mapped[List["Tag"]] = relationship(
        "Tag",
        secondary=change_issue_tags,
        primaryjoin=lambda: ChangeIssue.id == change_issue_tags.c.changeissue_id,
        secondaryjoin=lambda: (
            (Tag.workspace_id == change_issue_tags.c.tag_workspace_id)
            & (Tag.label == change_issue_tags.c.tag_label)
        ),
    )


from app.models.part import Tag  # noqa: E402
