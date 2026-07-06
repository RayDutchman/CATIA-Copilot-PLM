"""PartIteration ORM 模型，映射 partiteration 表。"""
from typing import Optional, List
from sqlalchemy import (
    Column, String, Integer, DateTime, Float,
    ForeignKey, ForeignKeyConstraint, Table, Boolean, BigInteger,
)
from sqlalchemy.orm import relationship, Mapped
from app.core.database import Base


# ── PartIteration 关联表 ──────────────────────────────────────

part_iteration_documentlink = Table(
    "partiteration_documentlink", Base.metadata,
    Column("workspace_id", String, primary_key=True),
    Column("partmaster_partnumber", String, primary_key=True),
    Column("partrevision_version", String, primary_key=True),
    Column("iteration", Integer, primary_key=True),
    Column("documentlink_id", Integer, primary_key=True),
    ForeignKeyConstraint(
        ["workspace_id", "partmaster_partnumber", "partrevision_version", "iteration"],
        ["partiteration.workspace_id", "partiteration.partmaster_partnumber",
         "partiteration.partrevision_version", "partiteration.iteration"],
    ),
)

part_iteration_attribute = Table(
    "partiteration_attribute", Base.metadata,
    Column("workspace_id", String, primary_key=True),
    Column("partmaster_partnumber", String, primary_key=True),
    Column("partrevision_version", String, primary_key=True),
    Column("iteration", Integer, primary_key=True),
    Column("instanceattribute_id", Integer, primary_key=True),
    Column("attribute_order", Integer),
    ForeignKeyConstraint(
        ["workspace_id", "partmaster_partnumber", "partrevision_version", "iteration"],
        ["partiteration.workspace_id", "partiteration.partmaster_partnumber",
         "partiteration.partrevision_version", "partiteration.iteration"],
    ),
)

part_iteration_pathdata_attr = Table(
    "partiteration_pathdata_attr", Base.metadata,
    Column("workspace_id", String, primary_key=True),
    Column("partmaster_partnumber", String, primary_key=True),
    Column("partrevision_version", String, primary_key=True),
    Column("iteration", Integer, primary_key=True),
    Column("instanceattribute_template_id", Integer, primary_key=True),
    Column("attribute_order", Integer),
    ForeignKeyConstraint(
        ["workspace_id", "partmaster_partnumber", "partrevision_version", "iteration"],
        ["partiteration.workspace_id", "partiteration.partmaster_partnumber",
         "partiteration.partrevision_version", "partiteration.iteration"],
    ),
)

part_iteration_binres = Table(
    "partiteration_binres", Base.metadata,
    Column("workspace_id", String, primary_key=True),
    Column("partmaster_partnumber", String, primary_key=True),
    Column("partrevision_version", String, primary_key=True),
    Column("iteration", Integer, primary_key=True),
    Column("attachedfile_fullname", String,
           ForeignKey("binaryresource.fullname"), primary_key=True),
    ForeignKeyConstraint(
        ["workspace_id", "partmaster_partnumber", "partrevision_version", "iteration"],
        ["partiteration.workspace_id", "partiteration.partmaster_partnumber",
         "partiteration.partrevision_version", "partiteration.iteration"],
    ),
)

part_iteration_geometry = Table(
    "partiteration_geometry", Base.metadata,
    Column("workspace_id", String, primary_key=True),
    Column("partmaster_partnumber", String, primary_key=True),
    Column("partrevision_version", String, primary_key=True),
    Column("iteration", Integer, primary_key=True),
    Column("geometry_fullname", String,
           ForeignKey("binaryresource.fullname"), primary_key=True),
    ForeignKeyConstraint(
        ["workspace_id", "partmaster_partnumber", "partrevision_version", "iteration"],
        ["partiteration.workspace_id", "partiteration.partmaster_partnumber",
         "partiteration.partrevision_version", "partiteration.iteration"],
    ),
)

part_iteration_usagelink = Table(
    "partiteration_partusagelink", Base.metadata,
    Column("workspace_id", String, primary_key=True),
    Column("partmaster_partnumber", String, primary_key=True),
    Column("partrevision_version", String, primary_key=True),
    Column("iteration", Integer, primary_key=True),
    Column("component_id", Integer,
           ForeignKey("partusagelink.id"), primary_key=True),
    Column("component_order", Integer),
    ForeignKeyConstraint(
        ["workspace_id", "partmaster_partnumber", "partrevision_version", "iteration"],
        ["partiteration.workspace_id", "partiteration.partmaster_partnumber",
         "partiteration.partrevision_version", "partiteration.iteration"],
    ),
)


class PartIteration(Base):
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

    native_cad_file_fullname = Column("nativecadfile_fullname", String,
                                      ForeignKey("binaryresource.fullname"))

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
    conversions: Mapped[List["Conversion"]] = relationship(
        "Conversion",
        primaryjoin=lambda: (
            (PartIteration.workspace_id == Conversion.workspace_id)
            & (PartIteration.partmaster_partnumber == Conversion.partmaster_partnumber)
            & (PartIteration.partrevision_version == Conversion.partrevision_version)
            & (PartIteration.iteration == Conversion.iteration)
        ),
        cascade="all, delete-orphan",
    )


from app.models.part import BinaryResource  # noqa: E402
from app.models.product.conversion import Conversion  # noqa: E402
from app.models.product.part_usage_link import PartUsageLink  # noqa: E402
