"""ProductInstanceMaster ORM 模型，映射 productinstancemaster 表。"""
from sqlalchemy import Column, String, Integer
from app.core.database import Base


class ProductInstanceMaster(Base):
    __tablename__ = "productinstancemaster"

    serialnumber = Column("serialnumber", String, primary_key=True)
    workspace_id = Column(String, primary_key=True)
    configurationitem_id = Column(String, primary_key=True)
    acl_id = Column(Integer)
