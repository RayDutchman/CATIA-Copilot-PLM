"""产品相关 Pydantic DTO，字段名与 DocdokuPLM JSON 响应完全一致（camelCase）。"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typing import Optional, List

class BaselinedPartDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    partNumber: Optional[str] = None
    version: Optional[str] = None
    iteration: Optional[int] = None



class ConfigurationItemLatestRevisionDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    partNumber: Optional[str] = None
    version: Optional[str] = None
    status: Optional[int] = None



class ProductBaselineDetailDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: Optional[int] = None
    name: Optional[str] = None
    type: Optional[str] = None
    configurationItemId: Optional[str] = None
    creationDate: Optional[str] = None
    description: Optional[str] = None
    author: Optional[UserDTO] = None
    hasObsoletePartRevisions: bool = False
    configurationItemLatestRevision: Optional[str] = None
    baselinedParts: List[BaselinedPartDTO] = []
    substituteLinks: List[dict] = []
    optionalUsageLinks: List[dict] = []
    pathToPathLinks: List[dict] = []
    substitutesParts: List[dict] = []
    optionalsParts: List[dict] = []



from app.schemas.part import UserDTO

# Re-exports from split files
from app.schemas.product.configuration_item import ConfigurationItemDTO  # noqa: E402, F401
from app.schemas.product.product_baseline import ProductBaselineSummaryDTO  # noqa: E402, F401
from app.schemas.product.product_configuration import ProductConfigurationDTO  # noqa: E402, F401
from app.schemas.product.product_instance_iteration import ProductInstanceIterationDTO  # noqa: E402, F401
from app.schemas.product.product_instance_master import ProductInstanceDTO  # noqa: E402, F401
from app.schemas.product.layer import LayerDTO  # noqa: E402, F401
from app.schemas.product.marker import MarkerDTO  # noqa: E402, F401

UserDTO.model_rebuild()
ConfigurationItemDTO.model_rebuild()
ProductBaselineSummaryDTO.model_rebuild()
ProductConfigurationDTO.model_rebuild()
ProductInstanceIterationDTO.model_rebuild()
ProductInstanceDTO.model_rebuild()
LayerDTO.model_rebuild()
MarkerDTO.model_rebuild()
