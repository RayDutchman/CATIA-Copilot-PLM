"""DocumentMasterTemplate ORM 模型，映射 documentmastertemplate 表。"""
from sqlalchemy import Column, String, Boolean, Integer, DateTime
from app.core.database import Base


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
