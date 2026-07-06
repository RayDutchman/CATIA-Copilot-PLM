"""DTO: ImportPreviewDTO."""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class ImportPreviewDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    partRevsToCheckout: List["LightPartRevisionDTO"] = []
    partsToCreate: List["PartCreationDTO"] = []


# 延迟导入避免循环引用
from app.schemas.part.light_part_revision import LightPartRevisionDTO  # noqa: E402
from app.schemas.part.part_creation import PartCreationDTO  # noqa: E402

ImportPreviewDTO.model_rebuild()
