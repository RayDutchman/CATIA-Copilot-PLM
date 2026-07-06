"""Folder meta ORM 模型 — 映射 folder 表（meta 域）。"""
from sqlalchemy import Column, String, ForeignKey
from app.core.database import Base

class Folder(Base):
    __tablename__ = "folder"
    completepath = Column("completepath", String, primary_key=True)
    parentfolder_completepath = Column("parentfolder_completepath", String, ForeignKey("folder.completepath"))
