"""零件相关 Pydantic DTO，字段名与 DocdokuPLM JSON 响应完全一致（camelCase）。"""
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class AclIdDTO(BaseModel):
    """ACL 更新响应"""
    model_config = ConfigDict(extra='forbid')
    aclId: Optional[int] = None



class CountDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    count: int = 0



class GeneratedIdDTO(BaseModel):
    """generate_id 响应"""
    model_config = ConfigDict(extra='forbid')
    generatedId: str



class PartIterationUpdateDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    iterationNote: Optional[str] = None
    instanceAttributes: Optional[List[dict]] = None
    instanceAttributeTemplates: Optional[List[dict]] = None
    components: Optional[List[PartUsageLinkDTO]] = None
    linkedDocuments: Optional[List[dict]] = None



class PositionDTO(BaseModel):
    """CAD 装配体组件位置信息（3x3 旋转矩阵 + 平移向量）。"""
    model_config = ConfigDict(extra='forbid')
    translation: Optional[list[float]] = None          # [x, y, z]
    rotationmatrix: Optional[list[list[float]]] = None  # 3x3 matrix



class SharedPartDTO(BaseModel):
    """share endpoint 响应"""
    model_config = ConfigDict(extra='forbid')
    uuid: str
    workspaceId: str



class StatusDTO(BaseModel):
    """通用状态响应"""
    model_config = ConfigDict(extra='forbid')
    status: str
    message: Optional[str] = None



# Re-exports from split files
from app.schemas.part.user import UserDTO  # noqa: E402, F401
from app.schemas.part.binary_resource import BinaryResourceDTO  # noqa: E402, F401
from app.schemas.part.cad_instance import CADInstanceDTO  # noqa: E402, F401
from app.schemas.part.part_usage_link import PartUsageLinkDTO  # noqa: E402, F401
from app.schemas.part.component import ComponentDTO  # noqa: E402, F401
from app.schemas.part.part_iteration import PartIterationDTO  # noqa: E402, F401
from app.schemas.part.part_revision import PartRevisionDTO  # noqa: E402, F401
from app.schemas.part.part_creation import PartCreationDTO  # noqa: E402, F401
from app.schemas.part.conversion import ConversionDTO  # noqa: E402, F401
from app.schemas.part.conversion_result import ConversionResultDTO  # noqa: E402, F401
from app.schemas.part.light_part_master import LightPartMasterDTO  # noqa: E402, F401
from app.schemas.part.part_master_template import PartTemplateDTO  # noqa: E402, F401

# Forward-reference resolution (runs after all classes loaded)
PartUsageLinkDTO.model_rebuild()
ComponentDTO.model_rebuild()
PartRevisionDTO.model_rebuild()
PartIterationDTO.model_rebuild()
ConversionResultDTO.model_rebuild()
ConversionDTO.model_rebuild()
