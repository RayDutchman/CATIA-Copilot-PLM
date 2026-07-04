"""零件相关 Pydantic DTO，字段名与 DocdokuPLM JSON 响应完全一致（camelCase）。"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from pydantic import BaseModel, model_validator


class UserDTO(BaseModel):
    login: str
    name: Optional[str] = None
    email: Optional[str] = None
    language: Optional[str] = None
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
    component: Optional[ComponentDTO] = None
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
    components: Optional[List[ComponentDTO]] = None
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
    standard_part: bool = False
    workflow_model_id: Optional[str] = None
    template_id: Optional[str] = None
    acl: Optional[dict] = None

    class Config:
        populate_by_name = True


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


class ConversionResultDTO(BaseModel):
    tempDir: Optional[str] = None
    convertedFileLODs: Optional[dict] = None
    box: Optional[list[float]] = None
    errorOutput: Optional[str] = None


class CountDTO(BaseModel):
    count: int = 0


class LightPartMasterDTO(BaseModel):
    number: str
    name: str = ""

    class Config:
        from_attributes = True
