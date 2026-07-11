"""DTO: CADInstanceDTO. Auto-split from part.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class CADInstanceDTO(BaseModel):
    model_config = ConfigDict(extra='ignore')
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
    matrix: Optional[List[float]] = None   # CATIA 4x4/4x3 变换矩阵展平数组
