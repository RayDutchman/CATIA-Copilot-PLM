"""ProductInstanceIteration ORM 模型，映射 productinstanceiteration 表。"""
from sqlalchemy import Column, String, Integer, DateTime
from app.core.database import Base


class ProductInstanceIteration(Base):
    __tablename__ = "productinstanceiteration"

    workspace_id = Column(String, primary_key=True)
    configurationitem_id = Column(String, primary_key=True)
    prdinstancemaster_serialnumber = Column("prdinstancemaster_serialnumber", String, primary_key=True)
    iteration = Column(Integer, primary_key=True)
    creation_date = Column("creationdate", DateTime)
    modification_date = Column("modificationdate", DateTime)
    iteration_note = Column("iterationnote", String)
    productbaseline_id = Column(Integer)
    author_workspace_id = Column(String)
    author_login = Column(String)
    documentcollection_id = Column(Integer)
    partcollection_id = Column(Integer)
