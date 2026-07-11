"""DTO: ConversionResultDTO. Auto-split from part.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class ConversionResultDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    tempDir: Optional[str] = None
    convertedFileLODs: Optional[dict] = None
    box: Optional[list[float]] = None
    errorOutput: Optional[str] = None
    componentPositionMap: Optional[dict[str, list[PositionDTO]]] = None
    materials: Optional[list[str]] = None
    partIterationKey: Optional[dict] = None
