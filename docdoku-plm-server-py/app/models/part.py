"""零件相关基础 ORM 模型 — BinaryResource, Tag, SharedEntity。其他实体已拆分到 models.product.*。"""
from sqlalchemy import Column, String, Integer, Float, BigInteger, DateTime, Boolean
from app.core.database import Base


class BinaryResource(Base):
    """对应 binaryresource 表，存储文件元数据（不含文件内容）。"""
    __tablename__ = "binaryresource"

    full_name = Column("fullname", String, primary_key=True)
    dtype = Column(String)
    content_length = Column("contentlength", BigInteger)
    last_modified = Column("lastmodified", DateTime)
    quality = Column(Integer)
    x_min = Column("x_min", Float)
    x_max = Column("x_max", Float)
    y_min = Column("y_min", Float)
    y_max = Column("y_max", Float)
    z_min = Column("z_min", Float)
    z_max = Column("z_max", Float)


class Tag(Base):
    """对应 tag 表。"""
    __tablename__ = "tag"

    workspace_id = Column(String, primary_key=True)
    label = Column(String, primary_key=True)


class SharedEntity(Base):
    """对应 sharedentity 表（单表继承，dtype 区分 SharedPart/SharedDocument）。"""
    __tablename__ = "sharedentity"

    uuid = Column(String, primary_key=True)
    dtype = Column(String)
    creation_date = Column("creationdate", DateTime)
    expire_date = Column("expiredate", DateTime, nullable=True)
    password = Column(String, nullable=True)
    author_workspace_id = Column(String)
    author_login = Column(String)
    workspace_id = Column(String)
    entity_workspace_id = Column(String)
    partmaster_partnumber = Column(String, nullable=True)
    partrevision_version = Column(String, nullable=True)
    documentrevision_version = Column(String, nullable=True)
    documentmaster_id = Column(String, nullable=True)


# 向后兼容：从新位置重新导出拆分后的实体和关联表（放底部避免循环导入）
from app.models.product.cad_instance import CADInstance  # noqa: E402, F401
from app.models.product.conversion import Conversion  # noqa: E402, F401
from app.models.product.part_master import PartMaster  # noqa: E402, F401
from app.models.product.part_revision import PartRevision, part_revision_tags  # noqa: E402, F401
from app.models.product.part_iteration import (  # noqa: E402, F401
    PartIteration,
    part_iteration_documentlink,
    part_iteration_attribute,
    part_iteration_pathdata_attr,
    part_iteration_binres,
    part_iteration_geometry,
    part_iteration_usagelink,
)
from app.models.product.part_usage_link import PartUsageLink, usage_link_cadinstances  # noqa: E402, F401
from app.models.product.part_substitute_link import PartSubstituteLink, substitute_link_cadinstances  # noqa: E402, F401
from app.models.product.part_master_template import PartMasterTemplate  # noqa: E402, F401
from app.models.product.geometry import Geometry  # noqa: E402, F401
