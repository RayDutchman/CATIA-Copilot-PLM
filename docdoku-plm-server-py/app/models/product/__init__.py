"""ORM: configurationitem + Layer + Marker。配置基线/实例已移至 models.configuration。"""
from typing import Optional
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Text, ForeignKey
)
from sqlalchemy.orm import relationship, Mapped
from app.core.database import Base

# 从新位置导入
from app.models.product.configuration_item import ConfigurationItem  # noqa: F401


class Layer(Base):
    __tablename__ = "layer"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    color = Column(String)
    creation_date = Column("creationdate", DateTime)
    author_workspace_id = Column(String)
    author_login = Column(String)
    configurationitem_id = Column(String)
    configurationitem_workspace_id = Column(String)


class Marker(Base):
    __tablename__ = "marker"
    id = Column(Integer, primary_key=True, autoincrement=True)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    z = Column(Float, nullable=False)
    title = Column(String)
    description = Column(Text)
    creation_date = Column("creationdate", DateTime)
    author_workspace_id = Column(String)
    author_login = Column(String)


# 向后兼容：从 models.configuration 重新导出
from app.models.configuration.product_baseline import ProductBaseline  # noqa: E402, F401
from app.models.configuration.product_configuration import ProductConfiguration  # noqa: E402, F401
from app.models.configuration.product_instance_master import ProductInstanceMaster  # noqa: E402, F401
from app.models.configuration.product_instance_iteration import ProductInstanceIteration  # noqa: E402, F401
