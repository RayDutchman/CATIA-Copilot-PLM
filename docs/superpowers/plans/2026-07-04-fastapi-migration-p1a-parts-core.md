# FastAPI 迁移 P1a：零件核心 CRUD 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现零件三层模型 ORM、Schemas 和核心 CRUD，覆盖 CATIA Copilot 全部强依赖接口，完成后将 Nginx 零件路由切换到 FastAPI。

**Architecture:** SQLAlchemy ORM 映射现有 docdokuplm 数据库 9 张零件表；业务逻辑封装在 ProductService；零件号含 `-` 的路径用末尾正则 `^(.+)-([A-Z]+)$` 拆分。

**Tech Stack:** P0 基础上无新依赖。

## Global Constraints

- 不修改数据库 schema
- 路径前缀 `/docdoku-plm-server-rest/api` 不变
- 零件号可含 `-`，版本号仅 `[A-Z]+`，路径从末尾拆分
- createPart 在同一事务创建 PartMaster + PartRevision(A) + PartIteration(1) 并自动 checkout
- findOrCreatePartMaster：子件号不存在时自动创建空 PartMaster
- updateIteration 必须是当前签出用户
- 状态枚举 0=WIP, 1=RELEASED, 2=OBSOLETE，响应中转字符串
- 注释中文，命名英文

---

## 文件结构

    docdoku-plm-server-py/app/
    ├── models/part.py            【新建】ORM 模型
    ├── schemas/part.py           【新建】Pydantic DTO
    ├── services/product_service.py【新建】业务逻辑
    ├── routers/parts.py          【新建】集合路由
    ├── routers/part.py           【新建】单零件路由
    └── main.py                   【修改】注册路由

    tests/
    ├── test_part_models.py       【新建】
    ├── test_product_service.py   【新建】
    └── test_parts_api.py         【新建】

---

### Task 1：ORM 模型（app/models/part.py）

**Files:**
- Create: `docdoku-plm-server-py/app/models/part.py`
- Create: `docdoku-plm-server-py/tests/test_part_models.py`

**Interfaces:**
- Produces: `PartMaster`, `PartRevision`, `PartIteration`, `PartUsageLink`, `CADInstance`, `Conversion`, `BinaryResource`, `Tag`, `PartIterationBinRes`, `PartIterationGeometry`, `PartIterationUsageLink`

- [ ] **Step 1: 写失败测试**

    # tests/test_part_models.py
    from app.core.database import engine
    from sqlalchemy import text, inspect

    def test_partmaster_table_exists():
        insp = inspect(engine)
        assert "partmaster" in insp.get_table_names()

    def test_partrevision_table_exists():
        insp = inspect(engine)
        assert "partrevision" in insp.get_table_names()

    def test_partiteration_table_exists():
        insp = inspect(engine)
        assert "partiteration" in insp.get_table_names()

    def test_orm_query_partmaster(db):
        from app.models.part import PartMaster
        # 只验证查询不报错（可能返回空结果）
        result = db.query(PartMaster).limit(1).all()
        assert isinstance(result, list)

    def test_orm_query_partrevision(db):
        from app.models.part import PartRevision
        result = db.query(PartRevision).limit(1).all()
        assert isinstance(result, list)

- [ ] **Step 2: 运行确认失败**

    cd docdoku-plm-server-py && source venv/bin/activate
    pytest tests/test_part_models.py -v
    # 预期：ImportError: cannot import name 'PartMaster' from 'app.models.part'

- [ ] **Step 3: 写 app/models/part.py**

    """零件三层模型 ORM，映射现有 docdokuplm 数据库。不修改表结构。"""
    from datetime import datetime
    from typing import Optional, List
    from sqlalchemy import (
        Column, String, Boolean, Integer, Float, BigInteger,
        DateTime, Text, ForeignKey, ForeignKeyConstraint, Table
    )
    from sqlalchemy.orm import relationship, Mapped
    from app.core.database import Base


    # ── 关联表（多对多，无额外列）─────────────────────────────────────────

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

    # partrevision → 标签（M:N，通过 partrevision_tags 或类似表）
    # 注：DocdokuPLM 用 partrevision_tag 关联表，tag 表结构：(workspace_id, label)
    part_revision_tags = Table(
        "partrevision_tag", Base.metadata,
        Column("partrevision_workspace_id", String, primary_key=True),
        Column("partrevision_partmaster_partnumber", String, primary_key=True),
        Column("partrevision_version", String, primary_key=True),
        Column("tag_workspace_id", String, primary_key=True),
        Column("tag_label", String, primary_key=True),
    )


    # ── 主实体 ──────────────────────────────────────────────────────────

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
        )
        tags: Mapped[List["Tag"]] = relationship(
            "Tag",
            secondary=part_revision_tags,
            primaryjoin=(
                "and_(PartRevision.workspace_id==part_revision_tags.c.partrevision_workspace_id,"
                "PartRevision.partmaster_partnumber==part_revision_tags.c.partrevision_partmaster_partnumber,"
                "PartRevision.version==part_revision_tags.c.partrevision_version)"
            ),
            secondaryjoin=(
                "and_(Tag.workspace_id==part_revision_tags.c.tag_workspace_id,"
                "Tag.label==part_revision_tags.c.tag_label)"
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
            primaryjoin=(
                "and_(PartIteration.workspace_id==part_iteration_binres.c.workspace_id,"
                "PartIteration.partmaster_partnumber==part_iteration_binres.c.partmaster_partnumber,"
                "PartIteration.partrevision_version==part_iteration_binres.c.partrevision_version,"
                "PartIteration.iteration==part_iteration_binres.c.iteration)"
            ),
            secondaryjoin="BinaryResource.full_name==part_iteration_binres.c.attachedfile_fullname",
        )
        geometries: Mapped[List["BinaryResource"]] = relationship(
            "BinaryResource",
            secondary=part_iteration_geometry,
            primaryjoin=(
                "and_(PartIteration.workspace_id==part_iteration_geometry.c.workspace_id,"
                "PartIteration.partmaster_partnumber==part_iteration_geometry.c.partmaster_partnumber,"
                "PartIteration.partrevision_version==part_iteration_geometry.c.partrevision_version,"
                "PartIteration.iteration==part_iteration_geometry.c.iteration)"
            ),
            secondaryjoin="BinaryResource.full_name==part_iteration_geometry.c.geometry_fullname",
        )
        components: Mapped[List["PartUsageLink"]] = relationship(
            "PartUsageLink",
            secondary=part_iteration_usagelink,
            primaryjoin=(
                "and_(PartIteration.workspace_id==part_iteration_usagelink.c.workspace_id,"
                "PartIteration.partmaster_partnumber==part_iteration_usagelink.c.partmaster_partnumber,"
                "PartIteration.partrevision_version==part_iteration_usagelink.c.partrevision_version,"
                "PartIteration.iteration==part_iteration_usagelink.c.iteration)"
            ),
            secondaryjoin="PartUsageLink.id==part_iteration_usagelink.c.component_id",
            order_by="part_iteration_usagelink.c.component_order",
        )


    # 子件链接的 CAD 实例关联表
    usage_link_cadinstances = Table(
        "partusagelink_cadinstance", Base.metadata,
        Column("partusagelink_id", Integer, ForeignKey("partusagelink.id"), primary_key=True),
        Column("cadinstances_id", Integer, ForeignKey("cadinstance.id"), primary_key=True),
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

- [ ] **Step 4: 运行测试确认通过**

    pytest tests/test_part_models.py -v
    # 预期：4 passed

- [ ] **Step 5: Commit**

    git add docdoku-plm-server-py/app/models/part.py \
            docdoku-plm-server-py/tests/test_part_models.py
    git commit -m "feat(py): P1a Task1 零件 ORM 模型（9张表完整映射）"

---

### Task 2：Pydantic Schemas（app/schemas/part.py）

**Files:**
- Create: `docdoku-plm-server-py/app/schemas/part.py`
- Create: `docdoku-plm-server-py/tests/test_part_schemas.py`

**Interfaces:**
- Consumes: 无（纯 Pydantic，不依赖 ORM）
- Produces:
  - `UserDTO`, `BinaryResourceDTO`, `CADInstanceDTO`
  - `PartCreationDTO`（请求）
  - `PartRevisionDTO`, `PartIterationDTO`, `PartUsageLinkDTO`, `ConversionDTO`（响应）
  - `PartIterationUpdateDTO`（PUT iterations 请求体）
  - `CountDTO`, `LightPartMasterDTO`

- [ ] **Step 1: 写失败测试**

    # tests/test_part_schemas.py
    from app.schemas.part import PartRevisionDTO, PartCreationDTO, ConversionDTO

    def test_part_creation_dto_required_fields():
        """创建零件 DTO 只有 number 是必填。"""
        dto = PartCreationDTO(number="PART-001")
        assert dto.number == "PART-001"
        assert dto.name == ""
        assert dto.standard_part is False

    def test_part_revision_dto_part_key():
        """partKey 应为 number-version 拼接。"""
        dto = PartRevisionDTO(
            workspaceId="WS1", number="PART-001", version="A",
            name="Test Part"
        )
        assert dto.partKey == "PART-001-A"

    def test_conversion_dto_defaults():
        dto = ConversionDTO()
        assert dto.pending is False
        assert dto.succeed is False

    def test_part_revision_status_field():
        """status 字段接受字符串 WIP/RELEASED/OBSOLETE。"""
        dto = PartRevisionDTO(
            workspaceId="WS1", number="P", version="A",
            name="x", status="RELEASED"
        )
        assert dto.status == "RELEASED"

- [ ] **Step 2: 运行确认失败**

    pytest tests/test_part_schemas.py -v
    # 预期：ImportError

- [ ] **Step 3: 写 app/schemas/part.py**

    """零件相关 Pydantic DTO，字段名与 DocdokuPLM JSON 响应完全一致（camelCase）。"""
    from __future__ import annotations
    from datetime import datetime
    from typing import Optional, List
    from pydantic import BaseModel, model_validator


    class UserDTO(BaseModel):
        login: str
        name: Optional[str] = None
        email: Optional[str] = None
        workspaceId: Optional[str] = None

        class Config:
            from_attributes = True


    class BinaryResourceDTO(BaseModel):
        fullName: str
        name: Optional[str] = None
        contentLength: Optional[int] = None
        lastModified: Optional[datetime] = None

        class Config:
            from_attributes = True


    class CADInstanceDTO(BaseModel):
        rx: Optional[float] = None
        ry: Optional[float] = None
        rz: Optional[float] = None
        tx: Optional[float] = None
        ty: Optional[float] = None
        tz: Optional[float] = None
        rotationType: Optional[str] = None   # "ANGLE" or "MATRIX"
        # 旋转矩阵 3x3 展平为 9 个字段（与 Payara CADInstanceDTO 字段名一致）
        m00: Optional[float] = None; m01: Optional[float] = None; m02: Optional[float] = None
        m10: Optional[float] = None; m11: Optional[float] = None; m12: Optional[float] = None
        m20: Optional[float] = None; m21: Optional[float] = None; m22: Optional[float] = None


    class PartUsageLinkDTO(BaseModel):
        id: int = 0
        fullId: Optional[str] = None
        amount: float = 1.0
        comment: Optional[str] = None
        referenceDescription: Optional[str] = None
        unit: Optional[str] = None
        optional: bool = False
        component: Optional["ComponentDTO"] = None
        cadInstances: List[CADInstanceDTO] = []
        substitutes: List[dict] = []


    class ComponentDTO(BaseModel):
        """递归 BOM 节点，与 Payara ComponentDTO 字段完全一致。"""
        number: str
        name: str = ""
        version: Optional[str] = None
        iteration: int = 0
        assembly: bool = False
        substitute: bool = False
        optional: bool = False
        amount: float = 0
        unit: Optional[str] = None
        partUsageLinkId: Optional[str] = None
        partUsageLinkReferenceDescription: Optional[str] = None
        components: Optional[List["ComponentDTO"]] = None
        attributes: Optional[List[dict]] = None
        checkOutUser: Optional[UserDTO] = None
        checkOutDate: Optional[datetime] = None
        released: bool = False
        obsolete: bool = False
        lastIterationNumber: Optional[int] = None
        accessDeny: bool = False
        hasPathData: bool = False
        isVirtual: bool = False
        standardPart: bool = False
        description: Optional[str] = None
        author: Optional[str] = None
        authorLogin: Optional[str] = None
        path: Optional[str] = None


    PartUsageLinkDTO.model_rebuild()
    ComponentDTO.model_rebuild()


    class PartIterationDTO(BaseModel):
        workspaceId: str
        number: str
        version: str
        iteration: int
        name: str = ""
        iterationNote: Optional[str] = None
        author: Optional[UserDTO] = None
        creationDate: Optional[datetime] = None
        modificationDate: Optional[datetime] = None
        checkInDate: Optional[datetime] = None
        instanceAttributes: List[dict] = []
        nativeCADFile: Optional[BinaryResourceDTO] = None
        geometryFileURI: Optional[str] = None
        components: List[PartUsageLinkDTO] = []
        attachedFiles: List[BinaryResourceDTO] = []
        linkedDocuments: List[dict] = []

        class Config:
            from_attributes = True


    class PartRevisionDTO(BaseModel):
        workspaceId: str
        number: str
        version: str
        partKey: str = ""
        name: str = ""
        type: Optional[str] = None
        standardPart: bool = False
        author: Optional[UserDTO] = None
        creationDate: Optional[datetime] = None
        modificationDate: Optional[datetime] = None
        checkInDate: Optional[datetime] = None
        description: str = ""
        lastIterationNumber: int = 0
        partIterations: List[PartIterationDTO] = []
        checkOutUser: Optional[UserDTO] = None
        checkOutDate: Optional[datetime] = None
        status: Optional[str] = "WIP"
        tags: List[str] = []
        workflow: Optional[dict] = None
        lifeCycleState: Optional[str] = None
        acl: Optional[dict] = None
        publicShared: bool = False
        attributesLocked: bool = False
        releaseDate: Optional[datetime] = None
        releaseAuthor: Optional[UserDTO] = None
        obsoleteDate: Optional[datetime] = None
        obsoleteAuthor: Optional[UserDTO] = None
        notifications: List[dict] = []

        @model_validator(mode="after")
        def set_part_key(self) -> "PartRevisionDTO":
            if not self.partKey:
                self.partKey = f"{self.number}-{self.version}"
            return self

        class Config:
            from_attributes = True


    class PartCreationDTO(BaseModel):
        """POST /workspaces/{ws}/parts 请求体。"""
        number: str
        name: str = ""
        description: str = ""
        standard_part: bool = False   # 内部用 snake_case，序列化时映射
        workflow_model_id: Optional[str] = None
        template_id: Optional[str] = None
        acl: Optional[dict] = None

        class Config:
            populate_by_name = True
            # 接受前端发来的 camelCase
            alias_generator = None


    class PartIterationUpdateDTO(BaseModel):
        iterationNote: Optional[str] = None
        instanceAttributes: Optional[List[dict]] = None
        components: Optional[List[PartUsageLinkDTO]] = None
        linkedDocuments: Optional[List[dict]] = None


    class ConversionDTO(BaseModel):
        pending: bool = False
        succeed: bool = False
        startDate: Optional[datetime] = None
        endDate: Optional[datetime] = None


    class CountDTO(BaseModel):
        count: int = 0


    class LightPartMasterDTO(BaseModel):
        number: str
        name: str = ""

        class Config:
            from_attributes = True

- [ ] **Step 4: 运行测试确认通过**

    pytest tests/test_part_schemas.py -v
    # 预期：4 passed

- [ ] **Step 5: Commit**

    git add docdoku-plm-server-py/app/schemas/part.py \
            docdoku-plm-server-py/tests/test_part_schemas.py
    git commit -m "feat(py): P1a Task2 零件 Pydantic Schemas（PartRevisionDTO/PartCreationDTO 等）"

---

### Task 3: ProductService（app/services/product_service.py）

**Files:**
- Create: `docdoku-plm-server-py/app/services/product_service.py`
- Create: `docdoku-plm-server-py/tests/test_product_service.py`

**Interfaces:**
- Consumes: `PartMaster`, `PartRevision`, `PartIteration`, `PartUsageLink`, `CADInstance`, `Conversion`（Task 1）
- Produces:
  - `list_revisions(db, workspace_id, start, length) -> list[PartRevision]`
  - `count_parts(db, workspace_id) -> int`
  - `get_revision(db, workspace_id, number, version) -> PartRevision`
  - `get_latest_revision(db, workspace_id, number) -> PartRevision`
  - `create_part(db, workspace_id, creator_login, body: PartCreationDTO) -> PartRevision`
  - `delete_revision(db, workspace_id, number, version, user_login) -> None`
  - `checkout(db, workspace_id, number, version, user_login) -> PartRevision`
  - `checkin(db, workspace_id, number, version, user_login) -> PartRevision`
  - `undo_checkout(db, workspace_id, number, version, user_login) -> PartRevision`
  - `update_iteration(db, workspace_id, number, version, iteration, user_login, body: PartIterationUpdateDTO) -> PartRevision`
  - `get_conversion(db, workspace_id, number, version, iteration) -> Conversion`
  - `search_numbers(db, workspace_id, q, limit) -> list[PartMaster]`
  - `list_checked_out(db, workspace_id) -> list[PartRevision]`
  - `find_or_create_part_master(db, workspace_id, number) -> PartMaster`

- [ ] **Step 1: 写失败测试**

    # tests/test_product_service.py
    import pytest
    from app.services.product_service import ProductService
    from app.schemas.part import PartCreationDTO

    def test_list_revisions_returns_list(db):
        svc = ProductService()
        result = svc.list_revisions(db, "Workspace_0", 0, 10)
        assert isinstance(result, list)

    def test_count_parts_returns_int(db):
        svc = ProductService()
        count = svc.count_parts(db, "Workspace_0")
        assert isinstance(count, int)
        assert count >= 0

    def test_get_revision_not_found_raises_404(db):
        from fastapi import HTTPException
        svc = ProductService()
        with pytest.raises(HTTPException) as exc:
            svc.get_revision(db, "Workspace_0", "NONEXISTENT-PART", "A")
        assert exc.value.status_code == 404

    def test_get_latest_revision_not_found_raises_404(db):
        from fastapi import HTTPException
        svc = ProductService()
        with pytest.raises(HTTPException) as exc:
            svc.get_latest_revision(db, "Workspace_0", "NONEXISTENT-PART")
        assert exc.value.status_code == 404

    def test_find_or_create_creates_when_missing(db):
        import uuid
        svc = ProductService()
        fake_number = f"TEST-{uuid.uuid4().hex[:8].upper()}"
        master = svc.find_or_create_part_master(db, "Workspace_0", fake_number)
        assert master.number == fake_number
        # 清理
        db.delete(master)
        db.commit()

- [ ] **Step 2: 运行确认失败**

    pytest tests/test_product_service.py -v
    # 预期：ImportError

- [ ] **Step 3: 写 app/services/product_service.py**

    from datetime import datetime
    from typing import Optional
    from fastapi import HTTPException, status
    from sqlalchemy.orm import Session
    from app.models.part import (
        PartMaster, PartRevision, PartIteration,
        PartUsageLink, CADInstance, Conversion,
        part_iteration_usagelink, usage_link_cadinstances,
    )
    from app.schemas.part import PartCreationDTO, PartIterationUpdateDTO


    class ProductService:

        # ── 查询 ──────────────────────────────────────────────────────────

        def list_revisions(self, db: Session, workspace_id: str,
                           start: int = 0, length: int = 50) -> list:
            return (
                db.query(PartRevision)
                .filter(PartRevision.workspace_id == workspace_id)
                .order_by(PartRevision.partmaster_partnumber, PartRevision.version)
                .offset(start).limit(length).all()
            )

        def count_parts(self, db: Session, workspace_id: str) -> int:
            return (
                db.query(PartMaster)
                .filter(PartMaster.workspace_id == workspace_id)
                .count()
            )

        def get_revision(self, db: Session, workspace_id: str,
                         number: str, version: str) -> PartRevision:
            pr = (
                db.query(PartRevision)
                .filter(
                    PartRevision.workspace_id == workspace_id,
                    PartRevision.partmaster_partnumber == number,
                    PartRevision.version == version,
                )
                .first()
            )
            if pr is None:
                raise HTTPException(status_code=404,
                                    detail=f"Part {number}-{version} not found")
            return pr

        def get_latest_revision(self, db: Session, workspace_id: str,
                                number: str) -> PartRevision:
            master = (
                db.query(PartMaster)
                .filter(PartMaster.workspace_id == workspace_id,
                        PartMaster.number == number)
                .first()
            )
            if master is None or not master.revisions:
                raise HTTPException(status_code=404,
                                    detail=f"Part {number} not found")
            return master.last_revision

        def search_numbers(self, db: Session, workspace_id: str,
                           q: str, limit: int = 8) -> list:
            pattern = f"%{q}%"
            return (
                db.query(PartMaster)
                .filter(
                    PartMaster.workspace_id == workspace_id,
                    PartMaster.number.ilike(pattern),
                )
                .limit(limit).all()
            )

        def list_checked_out(self, db: Session, workspace_id: str) -> list:
            return (
                db.query(PartRevision)
                .filter(
                    PartRevision.workspace_id == workspace_id,
                    PartRevision.checkout_user_login.isnot(None),
                )
                .all()
            )

        def get_conversion(self, db: Session, workspace_id: str,
                           number: str, version: str, iteration: int
                           ) -> Optional[Conversion]:
            return (
                db.query(Conversion)
                .filter(
                    Conversion.workspace_id == workspace_id,
                    Conversion.partmaster_partnumber == number,
                    Conversion.partrevision_version == version,
                    Conversion.iteration == iteration,
                )
                .first()
            )

        # ── 辅助 ──────────────────────────────────────────────────────────

        def find_or_create_part_master(self, db: Session,
                                       workspace_id: str, number: str) -> PartMaster:
            master = (
                db.query(PartMaster)
                .filter(PartMaster.workspace_id == workspace_id,
                        PartMaster.number == number)
                .first()
            )
            if master is None:
                master = PartMaster(
                    workspace_id=workspace_id,
                    number=number,
                    creation_date=datetime.utcnow(),
                )
                db.add(master)
                db.flush()
            return master

        def _next_version(self, current: str) -> str:
            if not current:
                return "A"
            last_char = current[-1]
            if last_char == "Z":
                return current + "A"
            return current[:-1] + chr(ord(last_char) + 1)

        # ── 写操作 ────────────────────────────────────────────────────────

        def create_part(self, db: Session, workspace_id: str,
                        creator_login: str, body: PartCreationDTO) -> PartRevision:
            # 检查零件号唯一性
            existing = (
                db.query(PartMaster)
                .filter(PartMaster.workspace_id == workspace_id,
                        PartMaster.number == body.number)
                .first()
            )
            if existing:
                raise HTTPException(status_code=409,
                                    detail=f"Part {body.number} already exists")
            now = datetime.utcnow()
            # 创建 PartMaster
            master = PartMaster(
                workspace_id=workspace_id,
                number=body.number,
                name=body.name,
                standard_part=body.standard_part,
                creation_date=now,
                author_workspace_id=workspace_id,
                author_login=creator_login,
            )
            db.add(master)
            db.flush()
            # 创建首个 PartRevision（版本 A）
            revision = PartRevision(
                workspace_id=workspace_id,
                partmaster_partnumber=body.number,
                version="A",
                description=body.description,
                status=0,
                creation_date=now,
                author_workspace_id=workspace_id,
                author_login=creator_login,
                checkout_user_workspace_id=workspace_id,
                checkout_user_login=creator_login,
                check_out_date=now,
            )
            db.add(revision)
            db.flush()
            # 创建首个 PartIteration（iteration=1）
            iteration = PartIteration(
                workspace_id=workspace_id,
                partmaster_partnumber=body.number,
                partrevision_version="A",
                iteration=1,
                creation_date=now,
                author_workspace_id=workspace_id,
                author_login=creator_login,
            )
            db.add(iteration)
            db.commit()
            db.refresh(revision)
            return revision

        def delete_revision(self, db: Session, workspace_id: str,
                            number: str, version: str, user_login: str) -> None:
            pr = self.get_revision(db, workspace_id, number, version)
            if pr.checkout_user_login and pr.checkout_user_login != user_login:
                raise HTTPException(403, "Part is checked out by another user")
            if pr.status == 1:
                raise HTTPException(403, "Cannot delete a released revision")
            db.delete(pr)
            db.commit()

        def checkout(self, db: Session, workspace_id: str,
                     number: str, version: str, user_login: str) -> PartRevision:
            pr = self.get_revision(db, workspace_id, number, version)
            if pr.checkout_user_login:
                raise HTTPException(409,
                    f"Already checked out by {pr.checkout_user_login}")
            if pr.status != 0:
                raise HTTPException(403, "Cannot check out a released/obsolete revision")
            now = datetime.utcnow()
            pr.checkout_user_login = user_login
            pr.checkout_user_workspace_id = workspace_id
            pr.check_out_date = now
            # 新建迭代（iteration+1）
            last_iter = pr.last_iteration_number
            new_iter = PartIteration(
                workspace_id=workspace_id,
                partmaster_partnumber=number,
                partrevision_version=version,
                iteration=last_iter + 1,
                creation_date=now,
                author_workspace_id=workspace_id,
                author_login=user_login,
            )
            db.add(new_iter)
            db.commit()
            db.refresh(pr)
            return pr

        def checkin(self, db: Session, workspace_id: str,
                    number: str, version: str, user_login: str) -> PartRevision:
            pr = self.get_revision(db, workspace_id, number, version)
            if pr.checkout_user_login != user_login:
                raise HTTPException(403, "You have not checked out this part")
            now = datetime.utcnow()
            # 标记最新迭代为已签入
            last = pr.last_iteration
            if last:
                last.check_in_date = now
            # 清空签出信息
            pr.checkout_user_login = None
            pr.checkout_user_workspace_id = None
            pr.check_out_date = None
            db.commit()
            db.refresh(pr)
            return pr

        def undo_checkout(self, db: Session, workspace_id: str,
                          number: str, version: str, user_login: str) -> PartRevision:
            pr = self.get_revision(db, workspace_id, number, version)
            if pr.checkout_user_login != user_login:
                raise HTTPException(403, "You have not checked out this part")
            # 删除未签入的最新迭代
            last = pr.last_iteration
            if last and last.check_in_date is None:
                db.delete(last)
            pr.checkout_user_login = None
            pr.checkout_user_workspace_id = None
            pr.check_out_date = None
            db.commit()
            db.refresh(pr)
            return pr

        def update_iteration(self, db: Session, workspace_id: str,
                             number: str, version: str, iteration_num: int,
                             user_login: str,
                             body: PartIterationUpdateDTO) -> PartRevision:
            pr = self.get_revision(db, workspace_id, number, version)
            if pr.checkout_user_login != user_login:
                raise HTTPException(403, "Part is not checked out by you")
            # 找目标迭代
            target = next(
                (it for it in pr.iterations if it.iteration == iteration_num), None
            )
            if target is None:
                raise HTTPException(404, f"Iteration {iteration_num} not found")
            now = datetime.utcnow()
            target.modification_date = now
            if body.iterationNote is not None:
                target.iteration_note = body.iterationNote
            # 更新子件列表
            if body.components is not None:
                self._sync_components(db, target, body.components, workspace_id)
            db.commit()
            db.refresh(pr)
            return pr

        def _sync_components(self, db: Session, iteration: PartIteration,
                              components_dto: list, workspace_id: str) -> None:
            # 清空旧关联
            db.execute(
                part_iteration_usagelink.delete().where(
                    part_iteration_usagelink.c.workspace_id == iteration.workspace_id,
                    part_iteration_usagelink.c.partmaster_partnumber == iteration.partmaster_partnumber,
                    part_iteration_usagelink.c.partrevision_version == iteration.partrevision_version,
                    part_iteration_usagelink.c.iteration == iteration.iteration,
                )
            )
            for order, comp_dto in enumerate(components_dto):
                comp_number = comp_dto.component.number if comp_dto.component else None
                if not comp_number:
                    continue
                # 确保子件 PartMaster 存在
                self.find_or_create_part_master(db, workspace_id, comp_number)
                # 创建 PartUsageLink
                link = PartUsageLink(
                    amount=comp_dto.amount,
                    comment=comp_dto.comment,
                    optional=comp_dto.optional,
                    reference_description=comp_dto.referenceDescription,
                    unit=comp_dto.unit,
                    component_workspace_id=workspace_id,
                    component_partnumber=comp_number,
                )
                db.add(link)
                db.flush()
                # 处理 CAD 实例
                for cad_dto in (comp_dto.cadInstances or []):
                    cad = CADInstance(
                        rotation_type=cad_dto.rotationType,
                        rx=cad_dto.rx, ry=cad_dto.ry, rz=cad_dto.rz,
                        tx=cad_dto.tx, ty=cad_dto.ty, tz=cad_dto.tz,
                        m00=cad_dto.m00, m01=cad_dto.m01, m02=cad_dto.m02,
                        m10=cad_dto.m10, m11=cad_dto.m11, m12=cad_dto.m12,
                        m20=cad_dto.m20, m21=cad_dto.m21, m22=cad_dto.m22,
                    )
                    db.add(cad)
                    db.flush()
                    db.execute(
                        usage_link_cadinstances.insert().values(
                            partusagelink_id=link.id,
                            cadinstances_id=cad.id,
                        )
                    )
                # 建立迭代→链接关联
                db.execute(
                    part_iteration_usagelink.insert().values(
                        workspace_id=iteration.workspace_id,
                        partmaster_partnumber=iteration.partmaster_partnumber,
                        partrevision_version=iteration.partrevision_version,
                        iteration=iteration.iteration,
                        component_id=link.id,
                        component_order=order,
                    )
                )

- [ ] **Step 4: 运行测试确认通过**

    pytest tests/test_product_service.py -v
    # 预期：5 passed

- [ ] **Step 5: Commit**

    git add docdoku-plm-server-py/app/services/product_service.py \
            docdoku-plm-server-py/tests/test_product_service.py
    git commit -m "feat(py): P1a Task3 ProductService（CRUD+签出签入+装配同步）"

---

### Task 4: DTO 映射工具（app/services/part_mapper.py）

**Files:**
- Create: `docdoku-plm-server-py/app/services/part_mapper.py`

**Interfaces:**
- Consumes: `PartRevision`, `PartIteration`, `PartUsageLink`（Task 1）；所有 DTO（Task 2）
- Produces:
  - `map_revision(pr: PartRevision) -> PartRevisionDTO`
  - `map_iteration(it: PartIteration) -> PartIterationDTO`
  - `map_usage_link(link: PartUsageLink) -> PartUsageLinkDTO`

- [ ] **Step 1: 写 app/services/part_mapper.py**

    from app.models.part import PartRevision, PartIteration, PartUsageLink, BinaryResource
    from app.schemas.part import (
        PartRevisionDTO, PartIterationDTO, PartUsageLinkDTO,
        ComponentDTO, CADInstanceDTO, BinaryResourceDTO, UserDTO,
    )

    STATUS_MAP = {0: "WIP", 1: "RELEASED", 2: "OBSOLETE"}

    def _user_dto(workspace_id, login) -> UserDTO | None:
        if not login:
            return None
        return UserDTO(login=login, workspaceId=workspace_id)

    def _binary_dto(br: BinaryResource | None) -> BinaryResourceDTO | None:
        if br is None:
            return None
        name = br.full_name.split("/")[-1] if br.full_name else ""
        return BinaryResourceDTO(
            fullName=br.full_name,
            name=name,
            contentLength=br.content_length,
            lastModified=br.last_modified,
        )

    def map_cad_instance(cad) -> CADInstanceDTO:
        return CADInstanceDTO(
            rotationType=cad.rotation_type,
            rx=cad.rx, ry=cad.ry, rz=cad.rz,
            tx=cad.tx, ty=cad.ty, tz=cad.tz,
            m00=cad.m00, m01=cad.m01, m02=cad.m02,
            m10=cad.m10, m11=cad.m11, m12=cad.m12,
            m20=cad.m20, m21=cad.m21, m22=cad.m22,
        )

    def map_usage_link(link: PartUsageLink) -> PartUsageLinkDTO:
        comp_dto = None
        if link.component:
            comp_dto = ComponentDTO(
                number=link.component.number,
                name=link.component.name or "",
                standardPart=link.component.standard_part or False,
            )
        return PartUsageLinkDTO(
            id=link.id,
            amount=link.amount or 1.0,
            comment=link.comment,
            referenceDescription=link.reference_description,
            unit=link.unit,
            optional=link.optional or False,
            component=comp_dto,
            cadInstances=[map_cad_instance(c) for c in (link.cad_instances or [])],
        )

    def map_iteration(it: PartIteration) -> PartIterationDTO:
        return PartIterationDTO(
            workspaceId=it.workspace_id,
            number=it.partmaster_partnumber,
            version=it.partrevision_version,
            iteration=it.iteration,
            iterationNote=it.iteration_note,
            author=_user_dto(it.author_workspace_id, it.author_login),
            creationDate=it.creation_date,
            modificationDate=it.modification_date,
            checkInDate=it.check_in_date,
            nativeCADFile=_binary_dto(it.native_cad_file),
            attachedFiles=[_binary_dto(f) for f in (it.attached_files or []) if f],
            components=[map_usage_link(l) for l in (it.components or [])],
        )

    def map_revision(pr: PartRevision) -> PartRevisionDTO:
        master = pr.part_master
        iterations = sorted(pr.iterations or [], key=lambda x: x.iteration)
        last_it = iterations[-1] if iterations else None
        return PartRevisionDTO(
            workspaceId=pr.workspace_id,
            number=pr.partmaster_partnumber,
            version=pr.version,
            partKey=f"{pr.partmaster_partnumber}-{pr.version}",
            name=master.name if master else "",
            type=master.type if master else None,
            standardPart=(master.standard_part or False) if master else False,
            attributesLocked=(master.attributes_locked or False) if master else False,
            author=_user_dto(pr.author_workspace_id, pr.author_login),
            creationDate=pr.creation_date,
            checkInDate=last_it.check_in_date if last_it else None,
            description=pr.description or "",
            lastIterationNumber=last_it.iteration if last_it else 0,
            partIterations=[map_iteration(it) for it in iterations],
            checkOutUser=_user_dto(pr.checkout_user_workspace_id, pr.checkout_user_login),
            checkOutDate=pr.check_out_date,
            status=STATUS_MAP.get(pr.status, "WIP"),
            publicShared=pr.public_shared or False,
            releaseDate=pr.release_date,
            releaseAuthor=_user_dto(pr.release_user_workspace, pr.release_user_login),
            obsoleteDate=pr.obsolete_date,
            obsoleteAuthor=_user_dto(pr.obsolete_user_workspace, pr.obsolete_user_login),
            tags=[t.label for t in (pr.tags or [])],
        )

- [ ] **Step 2: Commit**

    git add docdoku-plm-server-py/app/services/part_mapper.py
    git commit -m "feat(py): P1a Task4 PartRevision->DTO 映射工具"

---

### Task 5: 路由（app/routers/parts.py + part.py）

**Files:**
- Create: `docdoku-plm-server-py/app/routers/parts.py`
- Create: `docdoku-plm-server-py/app/routers/part.py`
- Modify: `docdoku-plm-server-py/app/main.py`
- Create: `docdoku-plm-server-py/tests/test_parts_api.py`

**Interfaces:**
- Consumes: `ProductService`（Task 3）、`map_revision`（Task 4）、`get_current_user`（P0 Task 3）
- Produces: 以下所有端点（与 Payara 路径完全一致）

端点清单：

    GET  /workspaces/{ws}/parts                              -> list[PartRevisionDTO]
    GET  /workspaces/{ws}/parts/count                        -> CountDTO
    GET  /workspaces/{ws}/parts/numbers?q=                   -> list[LightPartMasterDTO]
    GET  /workspaces/{ws}/parts/checkedout                   -> list[PartRevisionDTO]
    GET  /workspaces/{ws}/parts/countCheckedOut              -> CountDTO
    GET  /workspaces/{ws}/parts/{pn}/latest-revision         -> PartRevisionDTO
    POST /workspaces/{ws}/parts                              -> PartRevisionDTO (201)
    GET  /workspaces/{ws}/parts/{part_key}                   -> PartRevisionDTO
    DELETE /workspaces/{ws}/parts/{part_key}                 -> 204
    PUT  /workspaces/{ws}/parts/{part_key}/checkout          -> PartRevisionDTO
    PUT  /workspaces/{ws}/parts/{part_key}/checkin           -> PartRevisionDTO
    PUT  /workspaces/{ws}/parts/{part_key}/undocheckout      -> PartRevisionDTO
    PUT  /workspaces/{ws}/parts/{part_key}/iterations/{iter} -> PartRevisionDTO
    GET  /workspaces/{ws}/parts/{part_key}/iterations/{iter}/conversion -> ConversionDTO

其中 `{part_key}` 形如 `PART-001-A`，需在路由处理函数内用正则拆分：

    import re
    def _split_part_key(part_key: str) -> tuple[str, str]:
        m = re.match(r'^(.+)-([A-Z]+)$', part_key)
        if not m:
            raise HTTPException(400, f"Invalid part key: {part_key}")
        return m.group(1), m.group(2)

- [ ] **Step 1: 写失败测试**

    # tests/test_parts_api.py
    import pytest
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    PREFIX = "/docdoku-plm-server-rest/api"

    def get_token():
        resp = client.post(f"{PREFIX}/auth/login",
                           json={"login": "admin", "password": "changeit"})
        return resp.headers["jwt"]

    def test_list_parts_requires_auth():
        resp = client.get(f"{PREFIX}/workspaces/Workspace_0/parts")
        assert resp.status_code == 401

    def test_list_parts_returns_list():
        token = get_token()
        resp = client.get(f"{PREFIX}/workspaces/Workspace_0/parts",
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_count_parts():
        token = get_token()
        resp = client.get(f"{PREFIX}/workspaces/Workspace_0/parts/count",
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert "count" in resp.json()

    def test_create_and_get_and_delete_part():
        import uuid
        token = get_token()
        headers = {"Authorization": f"Bearer {token}"}
        number = f"TEST-{uuid.uuid4().hex[:8].upper()}"
        # 创建
        resp = client.post(f"{PREFIX}/workspaces/Workspace_0/parts",
                           json={"number": number, "name": "Test Part"},
                           headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["number"] == number
        assert data["version"] == "A"
        assert data["checkOutUser"] is not None   # 创建后自动签出
        # 获取
        resp2 = client.get(f"{PREFIX}/workspaces/Workspace_0/parts/{number}-A",
                           headers=headers)
        assert resp2.status_code == 200
        # 签入后删除
        client.put(f"{PREFIX}/workspaces/Workspace_0/parts/{number}-A/checkin",
                   headers=headers)
        resp3 = client.delete(f"{PREFIX}/workspaces/Workspace_0/parts/{number}-A",
                              headers=headers)
        assert resp3.status_code == 204

    def test_latest_revision_not_found():
        token = get_token()
        resp = client.get(
            f"{PREFIX}/workspaces/Workspace_0/parts/NONEXISTENT-XYZ/latest-revision",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 404

    def test_checkout_checkin_cycle():
        import uuid
        token = get_token()
        headers = {"Authorization": f"Bearer {token}"}
        number = f"CKO-{uuid.uuid4().hex[:6].upper()}"
        # 创建（自动签出）
        client.post(f"{PREFIX}/workspaces/Workspace_0/parts",
                    json={"number": number}, headers=headers)
        # 签入
        resp = client.put(
            f"{PREFIX}/workspaces/Workspace_0/parts/{number}-A/checkin",
            headers=headers)
        assert resp.status_code == 200
        assert resp.json()["checkOutUser"] is None
        # 签出
        resp2 = client.put(
            f"{PREFIX}/workspaces/Workspace_0/parts/{number}-A/checkout",
            headers=headers)
        assert resp2.status_code == 200
        assert resp2.json()["checkOutUser"]["login"] == "admin"
        # 撤销签出
        resp3 = client.put(
            f"{PREFIX}/workspaces/Workspace_0/parts/{number}-A/undocheckout",
            headers=headers)
        assert resp3.status_code == 200
        assert resp3.json()["checkOutUser"] is None
        # 清理
        client.delete(f"{PREFIX}/workspaces/Workspace_0/parts/{number}-A",
                      headers=headers)

- [ ] **Step 2: 运行确认失败**

    pytest tests/test_parts_api.py -v
    # 预期：404 或 ImportError

- [ ] **Step 3: 写 app/routers/parts.py**

    import re
    from typing import Annotated
    from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
    from sqlalchemy.orm import Session
    from app.core.database import get_db
    from app.core.deps import get_current_user
    from app.models.auth import Account
    from app.schemas.part import PartRevisionDTO, PartCreationDTO, CountDTO, LightPartMasterDTO
    from app.services.product_service import ProductService
    from app.services.part_mapper import map_revision

    router = APIRouter()
    svc = ProductService()


    def _split_part_key(part_key: str) -> tuple[str, str]:
        m = re.match(r'^(.+)-([A-Z]+)$', part_key)
        if not m:
            raise HTTPException(400, f"Invalid part key format: {part_key}")
        return m.group(1), m.group(2)


    @router.get("/workspaces/{workspace_id}/parts", response_model=list[PartRevisionDTO])
    def list_parts(
        workspace_id: str,
        start: int = Query(0, ge=0),
        length: int = Query(50, ge=1, le=500),
        current_user: Account = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        revisions = svc.list_revisions(db, workspace_id, start, length)
        return [map_revision(pr) for pr in revisions]


    @router.get("/workspaces/{workspace_id}/parts/count", response_model=CountDTO)
    def count_parts(
        workspace_id: str,
        current_user: Account = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        return CountDTO(count=svc.count_parts(db, workspace_id))


    @router.get("/workspaces/{workspace_id}/parts/numbers",
                response_model=list[LightPartMasterDTO])
    def search_numbers(
        workspace_id: str,
        q: str = Query(""),
        current_user: Account = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        masters = svc.search_numbers(db, workspace_id, q)
        return [LightPartMasterDTO(number=m.number, name=m.name or "") for m in masters]


    @router.get("/workspaces/{workspace_id}/parts/checkedout",
                response_model=list[PartRevisionDTO])
    def list_checked_out(
        workspace_id: str,
        current_user: Account = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        revisions = svc.list_checked_out(db, workspace_id)
        return [map_revision(pr) for pr in revisions]


    @router.get("/workspaces/{workspace_id}/parts/countCheckedOut",
                response_model=CountDTO)
    def count_checked_out(
        workspace_id: str,
        current_user: Account = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        return CountDTO(count=len(svc.list_checked_out(db, workspace_id)))


    @router.get("/workspaces/{workspace_id}/parts/{part_number}/latest-revision",
                response_model=PartRevisionDTO)
    def get_latest_revision(
        workspace_id: str,
        part_number: str,
        current_user: Account = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        pr = svc.get_latest_revision(db, workspace_id, part_number)
        return map_revision(pr)


    @router.post("/workspaces/{workspace_id}/parts",
                 response_model=PartRevisionDTO, status_code=201)
    def create_part(
        workspace_id: str,
        body: PartCreationDTO,
        current_user: Account = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        pr = svc.create_part(db, workspace_id, current_user.login, body)
        return map_revision(pr)


    @router.get("/workspaces/{workspace_id}/parts/{part_key}",
                response_model=PartRevisionDTO)
    def get_part_revision(
        workspace_id: str,
        part_key: str,
        current_user: Account = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        number, version = _split_part_key(part_key)
        pr = svc.get_revision(db, workspace_id, number, version)
        return map_revision(pr)


    @router.delete("/workspaces/{workspace_id}/parts/{part_key}",
                   status_code=204)
    def delete_part_revision(
        workspace_id: str,
        part_key: str,
        current_user: Account = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        number, version = _split_part_key(part_key)
        svc.delete_revision(db, workspace_id, number, version, current_user.login)


    @router.put("/workspaces/{workspace_id}/parts/{part_key}/checkout",
                response_model=PartRevisionDTO)
    def checkout_part(
        workspace_id: str,
        part_key: str,
        current_user: Account = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        number, version = _split_part_key(part_key)
        pr = svc.checkout(db, workspace_id, number, version, current_user.login)
        return map_revision(pr)


    @router.put("/workspaces/{workspace_id}/parts/{part_key}/checkin",
                response_model=PartRevisionDTO)
    def checkin_part(
        workspace_id: str,
        part_key: str,
        current_user: Account = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        number, version = _split_part_key(part_key)
        pr = svc.checkin(db, workspace_id, number, version, current_user.login)
        return map_revision(pr)


    @router.put("/workspaces/{workspace_id}/parts/{part_key}/undocheckout",
                response_model=PartRevisionDTO)
    def undo_checkout_part(
        workspace_id: str,
        part_key: str,
        current_user: Account = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        number, version = _split_part_key(part_key)
        pr = svc.undo_checkout(db, workspace_id, number, version, current_user.login)
        return map_revision(pr)


    @router.put("/workspaces/{workspace_id}/parts/{part_key}/iterations/{iteration}",
                response_model=PartRevisionDTO)
    def update_iteration(
        workspace_id: str,
        part_key: str,
        iteration: int,
        body: "PartIterationUpdateDTO",
        current_user: Account = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        from app.schemas.part import PartIterationUpdateDTO
        number, version = _split_part_key(part_key)
        pr = svc.update_iteration(db, workspace_id, number, version,
                                   iteration, current_user.login, body)
        return map_revision(pr)


    @router.get(
        "/workspaces/{workspace_id}/parts/{part_key}/iterations/{iteration}/conversion",
        response_model="ConversionDTO",
    )
    def get_conversion_status(
        workspace_id: str,
        part_key: str,
        iteration: int,
        current_user: Account = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        from app.schemas.part import ConversionDTO
        number, version = _split_part_key(part_key)
        conv = svc.get_conversion(db, workspace_id, number, version, iteration)
        if conv is None:
            return ConversionDTO()
        return ConversionDTO(
            pending=conv.pending or False,
            succeed=conv.succeed or False,
            startDate=conv.start_date,
            endDate=conv.end_date,
        )

- [ ] **Step 4: 修改 app/main.py，注册新路由**

    在 main.py 的 `app.include_router(auth.router, prefix=API_PREFIX)` 后面添加：

    from app.routers import parts as parts_router
    app.include_router(parts_router.router, prefix=API_PREFIX)

- [ ] **Step 5: 运行测试确认通过**

    pytest tests/test_parts_api.py -v
    # 预期：7 passed（依赖真实数据库有 admin 账号和 Workspace_0）

- [ ] **Step 6: Commit**

    git add docdoku-plm-server-py/app/routers/parts.py \
            docdoku-plm-server-py/app/main.py \
            docdoku-plm-server-py/tests/test_parts_api.py
    git commit -m "feat(py): P1a Task5 零件路由（14个端点，含签出签入和BOM更新）"

---

### Task 6: Nginx 零件路由切换

**Files:**
- Modify: `docdoku-plm-docker/front/nginx.conf`

**Interfaces:**
- Produces: 将零件相关路径流量从 Payara `back` 切换到 FastAPI `back-py`

- [ ] **Step 1: 在 front/nginx.conf 中新增零件路由块**

    在已有的 auth 路由块下方，添加：

    location /docdoku-plm-server-rest/api/workspaces/ {
        set $backpy "back-py:8000";
        proxy_pass         http://$backpy;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        client_max_body_size 500m;
        add_header Access-Control-Expose-Headers "jwt" always;
    }

    注意：此规则覆盖所有 /workspaces/ 路径，包括零件、文档、产品等。
    如果 P2/P3 模块尚未实现，暂时只切换零件路径：

    location ~ ^/docdoku-plm-server-rest/api/workspaces/[^/]+/parts {
        set $backpy "back-py:8000";
        proxy_pass http://$backpy;
        ...
    }

- [ ] **Step 2: 重启 front 容器使 Nginx 配置生效**

    cd docdoku-plm-docker
    docker compose up -d --force-recreate --no-deps front

- [ ] **Step 3: 验证切换成功**

    curl -s http://localhost:8000/docdoku-plm-server-rest/api/workspaces/Workspace_0/parts/count \
      -H "Authorization: Bearer <token>" | jq .
    # 预期：{"count": N}，来自 FastAPI

    curl -s http://localhost:8009/docdoku-plm-server-rest/api/health
    # 预期：{"status": "ok", "backend": "fastapi"}

- [ ] **Step 4: 验证 CATIA Copilot 客户端可切换**

    将 catia_copilot 的客户端切换到 unified_client.py 或修改 api_client.py 的 base_url 指向新后端，
    运行一次完整的同步流程验证端到端功能。

- [ ] **Step 5: Commit**

    git add docdoku-plm-docker/front/nginx.conf
    git commit -m "feat(nginx): P1a Task6 零件路由切换到 FastAPI back-py"

---

## 验收标准

P1a 完成后，以下全部通过：

1. `pytest docdoku-plm-server-py/tests/ -v` 全部通过（≥ 20 个测试）
2. `POST /auth/login` + `GET /workspaces/{ws}/parts` 端到端正常
3. 创建零件 → 签出 → 更新迭代（含子件）→ 签入 → 删除完整流程通过测试
4. CATIA Copilot `api_client.py` 或 `unified_client.py` 指向 FastAPI 后端能完成零件同步
5. Backbone 前端零件列表页可正常加载数据

## 下一步：P1b

P1b 覆盖文件上传下载（CAD 文件 + 附件）、CAD 转换回调、状态管理（release/obsolete/tags）、搜索。
P1b 完成后 Payara back 容器可以退出零件相关功能。
