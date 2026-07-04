"""零件三层模型 ORM，映射现有 docdokuplm 数据库。不修改表结构。"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Boolean, Integer, Float, BigInteger,
    DateTime, Text, ForeignKey, Table
)
from sqlalchemy.orm import relationship, Mapped
from app.core.database import Base


# ── 关联表（多对多）──────────────────────────────────────────

# partiteration → 附件（M:N）
part_iteration_binres = Table(
    "partiteration_binres", Base.metadata,
    Column("workspace_id", String, primary_key=True),
    Column("partmaster_partnumber", String, primary_key=True),
    Column("partrevision_version", String, primary_key=True),
    Column("iteration", Integer, primary_key=True),
    Column("attachedfile_fullname", String,
           ForeignKey("binaryresource.fullname"), primary_key=True),
)

# partiteration → GLB 几何体（M:N）
part_iteration_geometry = Table(
    "partiteration_geometry", Base.metadata,
    Column("workspace_id", String, primary_key=True),
    Column("partmaster_partnumber", String, primary_key=True),
    Column("partrevision_version", String, primary_key=True),
    Column("iteration", Integer, primary_key=True),
    Column("geometry_fullname", String,
           ForeignKey("binaryresource.fullname"), primary_key=True),
)

# partiteration → 子件链接（有序 M:N）
part_iteration_usagelink = Table(
    "partiteration_partusagelink", Base.metadata,
    Column("workspace_id", String, primary_key=True),
    Column("partmaster_partnumber", String, primary_key=True),
    Column("partrevision_version", String, primary_key=True),
    Column("iteration", Integer, primary_key=True),
    Column("component_id", Integer,
           ForeignKey("partusagelink.id"), primary_key=True),
    Column("component_order", Integer),
)

# partrevision → 标签（M:N）
# 实际列名为 partmaster_workspace_id / partmaster_partnumber（非 partrevision_ 前缀）
part_revision_tags = Table(
    "partrevision_tag", Base.metadata,
    Column("partmaster_workspace_id", String, primary_key=True),
    Column("partmaster_partnumber", String, primary_key=True),
    Column("partrevision_version", String, primary_key=True),
    Column("tag_workspace_id", String, primary_key=True),
    Column("tag_label", String, primary_key=True),
)


# ── 主实体 ──────────────────────────────────────────────────

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


class CADInstance(Base):
    """对应 cadinstance 表，存储装配位置（欧拉角或旋转矩阵）。"""
    __tablename__ = "cadinstance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rotation_type = Column("rotationtype", String)   # "ANGLE" 或 "MATRIX"
    rx = Column(Float)
    ry = Column(Float)
    rz = Column(Float)
    tx = Column(Float)
    ty = Column(Float)
    tz = Column(Float)
    m00 = Column(Float); m01 = Column(Float); m02 = Column(Float)
    m10 = Column(Float); m11 = Column(Float); m12 = Column(Float)
    m20 = Column(Float); m21 = Column(Float); m22 = Column(Float)


class PartMaster(Base):
    """对应 partmaster 表，零件主数据（跨版本共享的信息）。"""
    __tablename__ = "partmaster"

    workspace_id = Column(String, primary_key=True)
    number = Column("partnumber", String, primary_key=True)
    name = Column(String)
    type = Column(String)
    standard_part = Column("standardpart", Boolean, default=False)
    attributes_locked = Column("attributeslocked", Boolean, default=False)
    creation_date = Column("creationdate", DateTime)
    author_workspace_id = Column(String)
    author_login = Column(String)

    # 关联：一个 PartMaster 有多个 PartRevision（按 version 排序）
    revisions: Mapped[List["PartRevision"]] = relationship(
        "PartRevision",
        foreign_keys="[PartRevision.workspace_id, PartRevision.partmaster_partnumber]",
        primaryjoin=(
            "and_(PartMaster.workspace_id==PartRevision.workspace_id,"
            "PartMaster.number==PartRevision.partmaster_partnumber)"
        ),
        order_by="PartRevision.version",
        back_populates="part_master",
    )

    @property
    def last_revision(self) -> Optional["PartRevision"]:
        """返回最新版本（版本字母最大）。"""
        if not self.revisions:
            return None
        return self.revisions[-1]


class PartRevision(Base):
    """对应 partrevision 表，零件的一个版本（A/B/C...）。"""
    __tablename__ = "partrevision"

    workspace_id = Column(String, primary_key=True)
    partmaster_partnumber = Column(String, primary_key=True)
    version = Column(String, primary_key=True)

    description = Column(Text)
    status = Column(Integer, default=0)         # 0=WIP, 1=RELEASED, 2=OBSOLETE
    public_shared = Column("publicshared", Boolean, default=False)
    creation_date = Column("creationdate", DateTime)
    check_out_date = Column("checkoutdate", DateTime)
    release_date = Column("release_date", DateTime)
    obsolete_date = Column("obsolete_date", DateTime)

    # 作者
    author_workspace_id = Column(String)
    author_login = Column(String)
    # 签出人
    checkout_user_workspace_id = Column("checkoutuser_workspace_id", String)
    checkout_user_login = Column("checkoutuser_login", String)
    # 发布人
    release_user_workspace = Column(String)
    release_user_login = Column(String)
    # 作废人
    obsolete_user_workspace = Column(String)
    obsolete_user_login = Column(String)

    acl_id = Column(Integer)
    workflow_id = Column(Integer)

    # 关联
    part_master: Mapped["PartMaster"] = relationship(
        "PartMaster",
        foreign_keys=[workspace_id, partmaster_partnumber],
        primaryjoin=(
            "and_(PartRevision.workspace_id==PartMaster.workspace_id,"
            "PartRevision.partmaster_partnumber==PartMaster.number)"
        ),
        back_populates="revisions",
    )
    iterations: Mapped[List["PartIteration"]] = relationship(
        "PartIteration",
        foreign_keys=(
            "PartIteration.workspace_id, PartIteration.partmaster_partnumber,"
            "PartIteration.partrevision_version"
        ),
        primaryjoin=(
            "and_(PartRevision.workspace_id==PartIteration.workspace_id,"
            "PartRevision.partmaster_partnumber==PartIteration.partmaster_partnumber,"
            "PartRevision.version==PartIteration.partrevision_version)"
        ),
        order_by="PartIteration.iteration",
        back_populates="revision",
        cascade="all, delete-orphan",
    )
    tags: Mapped[List["Tag"]] = relationship(
        "Tag",
        secondary=part_revision_tags,
        primaryjoin=lambda: (
            (PartRevision.workspace_id == part_revision_tags.c.partmaster_workspace_id)
            & (PartRevision.partmaster_partnumber == part_revision_tags.c.partmaster_partnumber)
            & (PartRevision.version == part_revision_tags.c.partrevision_version)
        ),
        secondaryjoin=lambda: (
            (Tag.workspace_id == part_revision_tags.c.tag_workspace_id)
            & (Tag.label == part_revision_tags.c.tag_label)
        ),
    )

    @property
    def last_iteration(self) -> Optional["PartIteration"]:
        if not self.iterations:
            return None
        return self.iterations[-1]

    @property
    def last_iteration_number(self) -> int:
        if not self.iterations:
            return 0
        return self.iterations[-1].iteration

    @property
    def status_label(self) -> str:
        return {0: "WIP", 1: "RELEASED", 2: "OBSOLETE"}.get(self.status, "WIP")


class PartIteration(Base):
    """对应 partiteration 表，零件版本的一次迭代（签出→修改→签入循环）。"""
    __tablename__ = "partiteration"

    workspace_id = Column(String, primary_key=True)
    partmaster_partnumber = Column(String, primary_key=True)
    partrevision_version = Column(String, primary_key=True)
    iteration = Column(Integer, primary_key=True)

    iteration_note = Column("iterationnote", String)
    source = Column(Integer)
    check_in_date = Column("checkindate", DateTime)
    creation_date = Column("creationdate", DateTime)
    modification_date = Column("modificationdate", DateTime)
    author_workspace_id = Column(String)
    author_login = Column(String)

    # 原生 CAD 文件（FK → binaryresource.fullname）
    native_cad_file_fullname = Column("nativecadfile_fullname", String,
                                      ForeignKey("binaryresource.fullname"))

    # 关联
    revision: Mapped["PartRevision"] = relationship(
        "PartRevision",
        foreign_keys=[workspace_id, partmaster_partnumber, partrevision_version],
        primaryjoin=(
            "and_(PartIteration.workspace_id==PartRevision.workspace_id,"
            "PartIteration.partmaster_partnumber==PartRevision.partmaster_partnumber,"
            "PartIteration.partrevision_version==PartRevision.version)"
        ),
        back_populates="iterations",
    )
    native_cad_file: Mapped[Optional["BinaryResource"]] = relationship(
        "BinaryResource",
        foreign_keys=[native_cad_file_fullname],
    )
    attached_files: Mapped[List["BinaryResource"]] = relationship(
        "BinaryResource",
        secondary=part_iteration_binres,
        primaryjoin=lambda: (
            (PartIteration.workspace_id == part_iteration_binres.c.workspace_id)
            & (PartIteration.partmaster_partnumber == part_iteration_binres.c.partmaster_partnumber)
            & (PartIteration.partrevision_version == part_iteration_binres.c.partrevision_version)
            & (PartIteration.iteration == part_iteration_binres.c.iteration)
        ),
        secondaryjoin=lambda: BinaryResource.full_name == part_iteration_binres.c.attachedfile_fullname,
    )
    geometries: Mapped[List["BinaryResource"]] = relationship(
        "BinaryResource",
        secondary=part_iteration_geometry,
        primaryjoin=lambda: (
            (PartIteration.workspace_id == part_iteration_geometry.c.workspace_id)
            & (PartIteration.partmaster_partnumber == part_iteration_geometry.c.partmaster_partnumber)
            & (PartIteration.partrevision_version == part_iteration_geometry.c.partrevision_version)
            & (PartIteration.iteration == part_iteration_geometry.c.iteration)
        ),
        secondaryjoin=lambda: BinaryResource.full_name == part_iteration_geometry.c.geometry_fullname,
    )
    components: Mapped[List["PartUsageLink"]] = relationship(
        "PartUsageLink",
        secondary=part_iteration_usagelink,
        primaryjoin=lambda: (
            (PartIteration.workspace_id == part_iteration_usagelink.c.workspace_id)
            & (PartIteration.partmaster_partnumber == part_iteration_usagelink.c.partmaster_partnumber)
            & (PartIteration.partrevision_version == part_iteration_usagelink.c.partrevision_version)
            & (PartIteration.iteration == part_iteration_usagelink.c.iteration)
        ),
        secondaryjoin=lambda: PartUsageLink.id == part_iteration_usagelink.c.component_id,
        order_by=part_iteration_usagelink.c.component_order,
    )


# 子件链接的 CAD 实例关联表
# 实际列名为 cadinstance_id（单数，非 cadinstances_id）
usage_link_cadinstances = Table(
    "partusagelink_cadinstance", Base.metadata,
    Column("partusagelink_id", Integer, ForeignKey("partusagelink.id"), primary_key=True),
    Column("cadinstance_id", Integer, ForeignKey("cadinstance.id"), primary_key=True),
    Column("cadinstance_order", Integer),
)


class PartUsageLink(Base):
    """对应 partusagelink 表，装配子件链接（包含数量、可选、注释等）。"""
    __tablename__ = "partusagelink"

    id = Column(Integer, primary_key=True, autoincrement=True)
    amount = Column(Float, default=1.0)
    comment = Column("commentdata", String)
    optional = Column(Boolean, default=False)
    reference_description = Column("referencedescription", String)
    unit = Column(String)
    component_workspace_id = Column(String)
    component_partnumber = Column(String)

    # 关联
    component: Mapped[Optional["PartMaster"]] = relationship(
        "PartMaster",
        foreign_keys=[component_workspace_id, component_partnumber],
        primaryjoin=(
            "and_(PartUsageLink.component_workspace_id==PartMaster.workspace_id,"
            "PartUsageLink.component_partnumber==PartMaster.number)"
        ),
    )
    cad_instances: Mapped[List["CADInstance"]] = relationship(
        "CADInstance",
        secondary=usage_link_cadinstances,
    )


class Conversion(Base):
    """对应 conversion 表，记录 CAD 转换任务状态。"""
    __tablename__ = "conversion"

    workspace_id = Column(String, primary_key=True)
    partmaster_partnumber = Column(String, primary_key=True)
    partrevision_version = Column(String, primary_key=True)
    iteration = Column(Integer, primary_key=True)
    pending = Column(Boolean, default=True)
    succeed = Column(Boolean, default=False)
    start_date = Column("startdate", DateTime)
    end_date = Column("enddate", DateTime)
