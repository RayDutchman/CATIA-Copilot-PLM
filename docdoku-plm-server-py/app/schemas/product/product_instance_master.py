"""DTO: ProductInstanceMasterDTO."""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class ProductInstanceMasterDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    identifier: Optional[str] = None
    serialNumber: Optional[str] = None
    configurationItemId: Optional[str] = None
    productInstanceIterations: List["ProductInstanceIterationDTO"] = []
    acl: Optional[dict] = None


from app.schemas.product.product_instance_iteration import ProductInstanceIterationDTO  # noqa: E402

ProductInstanceMasterDTO.model_rebuild()
ProductInstanceDTO = ProductInstanceMasterDTO  # 兼容旧名称
