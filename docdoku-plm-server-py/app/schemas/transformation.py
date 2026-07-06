"""DTO: TransformationDTO."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict


class TransformationDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    tx: float = 0.0
    ty: float = 0.0
    tz: float = 0.0
    rx: float = 0.0
    ry: float = 0.0
    rz: float = 0.0
